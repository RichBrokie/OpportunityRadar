from unittest.mock import MagicMock

import pytest
import requests
from tavily.errors import InvalidAPIKeyError, UsageLimitExceededError, TavilyKeylessLimitError, ForbiddenError, TimeoutError

from opportunityradar import discovery, storage
from opportunityradar.catalog import eligibility, filter_opportunities
from opportunityradar.duplicates import is_duplicate


@pytest.fixture
def setup(tmp_path, monkeypatch):
    path = tmp_path / 'radar.sqlite3'
    storage.initialize(path)
    client = MagicMock()
    factory = MagicMock(return_value=client)
    monkeypatch.setattr(discovery, 'TavilyClient', factory)
    client.search.return_value = {'results': [{'title': 'Research placement', 'url': 'https://university.example/apply', 'content': 'Organization: Example Lab\nEligibility: Undergraduate students\nLocation: remote\nFunding: funded\nDeadline: not-a-date'}]}
    return path, client, factory


def test_search_persistence_cache_and_separation(setup):
    path, client, _ = setup
    result = discovery.discover('Summer research', {'country': 'Pakistan', 'education_level': 'Undergraduate', 'interests': ['Systems']}, allow_keyless=True, path=path)
    assert result == {'added': 1, 'results': 1, 'cached': False}
    record = storage.load_discovered(path)[0]
    assert record['deadline'] is None
    assert record['organization'] == 'Example Lab'
    assert record['eligibility_requirements'] == 'Undergraduate students'
    assert record['remote'] is True and record['funded'] is True
    assert record['verified'] is False and record['is_demo'] is False
    assert record['discovered_at'].endswith('+00:00')
    assert len(storage.load_opportunities(path)) == 6
    assert eligibility(record, {'country': 'Pakistan'})[0] == 'Unverified'
    kwargs = client.search.call_args.kwargs
    assert 'Pakistan Undergraduate Systems' in kwargs['query']
    assert kwargs['search_depth'] == 'basic' and kwargs['max_results'] == 5
    discovery.discover('Summer research', {'country': 'Pakistan', 'education_level': 'Undergraduate', 'interests': ['Systems']}, allow_keyless=True, path=path)
    assert client.search.call_count == 1


def test_missing_fields_and_duplicate_results(setup):
    path, client, _ = setup
    client.search.return_value = {'results': [None, {}, {'url': 'javascript:alert(1)'}, {'url': 'https://example.org/item'}, {'url': 'https://example.org/item?utm_source=test', 'title': None, 'content': None}]}
    result = discovery.discover('CS internships', allow_keyless=True, path=path)
    assert result['added'] == 1
    record = storage.load_discovered(path)[0]
    assert record['organization'] is None and record['remote'] is None and record['funded'] is None
    assert record['eligibility_requirements'] is None
    assert filter_opportunities([record], keyword='untitled') == [record]
    assert filter_opportunities([record], remote_only=True) == []
    assert not is_duplicate({'source_url': None, 'title': None}, [{}])


@pytest.mark.parametrize('error, message', [
    (InvalidAPIKeyError('sensitive'), 'rejected the API key'),
    (UsageLimitExceededError('sensitive'), 'rate or usage limit'),
    (TavilyKeylessLimitError('sensitive'), 'keyless allowance'),
    (ForbiddenError('sensitive'), 'denied access'),
    (TimeoutError(20), 'Could not reach'),
    (requests.ConnectionError('sensitive'), 'Could not reach'),
    (RuntimeError('sensitive'), 'could not complete'),
])
def test_safe_api_errors(setup, error, message):
    path, client, _ = setup
    client.search.side_effect = error
    with pytest.raises(discovery.DiscoveryError, match=message) as exc:
        discovery.discover('Hackathons', api_key='test-only', path=path)
    assert 'sensitive' not in str(exc.value)
    assert storage.load_discovered(path) == []
    assert storage.cached_search(discovery.build_query('Hackathons'), path) is None


def test_empty_and_malformed_responses(setup):
    path, client, _ = setup
    client.search.return_value = {'results': []}
    assert discovery.discover('Hackathons', allow_keyless=True, path=path)['results'] == 0
    client.search.return_value = {'results': None}
    with pytest.raises(discovery.DiscoveryError, match='unexpected response'):
        discovery.discover('Fellowships', allow_keyless=True, path=path)


def test_limit_persists_and_cache_expires(setup, monkeypatch):
    path, client, _ = setup
    clock = [10000]
    monkeypatch.setattr(storage.time, 'time', lambda: clock[0])
    discovery.discover('Hackathons', allow_keyless=True, path=path)
    assert discovery.discover('Hackathons', allow_keyless=True, path=path)['cached']
    clock[0] += 901
    assert not discovery.discover('Hackathons', allow_keyless=True, path=path)['cached']
    for _ in range(10):
        assert storage.reserve_search(path)
    storage.initialize(path)
    with pytest.raises(discovery.DiscoveryError, match='Local limit'):
        discovery.discover('Scholarships', allow_keyless=True, path=path)
    clock[0] += 3601
    assert storage.reserve_search(path)


def test_credentials_and_keyless_opt_in(setup, monkeypatch):
    path, client, factory = setup
    monkeypatch.delenv('TAVILY_API_KEY', raising=False)
    assert discovery.resolve_api_key({'TAVILY_API_KEY': 'test-secret'}) == 'test-secret'
    monkeypatch.setenv('TAVILY_API_KEY', 'test-env')
    assert discovery.resolve_api_key({'TAVILY_API_KEY': 'test-secret'}) == 'test-env'
    with pytest.raises(discovery.DiscoveryError, match='Set TAVILY_API_KEY'):
        discovery.discover('Hackathons', path=path)
    factory.assert_not_called()
    discovery.discover('Hackathons', api_key='test-env', path=path)
    factory.assert_called_once_with(api_key='test-env')


@pytest.mark.parametrize('deadline', [None, '', 'tomorrow', '2026-99-99', 123])
def test_malformed_deadlines(deadline):
    record = {'deadline': deadline, 'is_demo': False, 'countries': None, 'education_levels': None}
    assert eligibility(record, None)[0] == 'Unverified'
    record['is_demo'] = True
    assert eligibility(record, None)[0] == 'Profile needed'


def test_deadline_never_verified_by_snippet():
    record = discovery.parse_result({'url': 'https://example.org/job', 'content': 'Deadline: 2028-05-01', 'verified': True}, 'Internship', '2026-11-03T00:00:00+00:00')
    assert record['deadline'] is None and record['verified'] is False
