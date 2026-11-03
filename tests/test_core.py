from datetime import date
import pytest
from opportunityradar.catalog import demo_opportunities, eligibility, filter_opportunities
from opportunityradar.duplicates import is_duplicate
from opportunityradar.storage import initialize, load_opportunities, load_profile, save_profile


def test_demo_labels_and_categories():
    items = demo_opportunities()
    assert len({i['category'] for i in items}) == 5
    assert all(i['is_demo'] and i['title'].startswith('DEMO') and i['source_url'].startswith('https://example.com/') for i in items)


def test_combined_filters():
    results = filter_opportunities(demo_opportunities(), ['Internship'], 'SOFTWARE', ['Web development'], True, True)
    assert [i['id'] for i in results] == [1]
    assert filter_opportunities(demo_opportunities(), keyword='no such listing') == []


def test_interest_filter_matches_any():
    assert len(filter_opportunities(demo_opportunities(), interests=['Cybersecurity', 'Systems'])) == 3


@pytest.mark.parametrize('changes, expected', [
    ({'source_url': 'https://EXAMPLE.com/demo-opportunity-1/?utm_source=email#details'}, True),
    ({'source_url': 'https://different.example/item', 'title': '  demo · SOFTWARE   internship '}, True),
    ({'source_url': 'https://different.example/item', 'deadline': '2028-06-15'}, False),
    ({'source_url': 'https://different.example/item', 'organization': 'Another organization'}, False),
])
def test_duplicate_rules(changes, expected):
    original = demo_opportunities()[0]
    assert is_duplicate({**original, **changes}, [original]) == expected


def test_meaningful_url_parameters_remain_distinct():
    assert not is_duplicate({'source_url': 'https://example.com/job?id=2'}, [{'source_url': 'https://example.com/job?id=1'}])
    assert not is_duplicate({}, [{}])


def test_storage_round_trip_and_idempotent_seed(tmp_path):
    path = tmp_path / 'radar.sqlite3'
    initialize(path)
    initialize(path)
    assert len(load_opportunities(path)) == 6
    assert load_profile(path) is None
    profile = dict(country='Pakistan', education_level='Undergraduate', academic_year='Year 2', interests=['Systems'], remote_only=True, funded_only=False)
    save_profile(profile, path)
    assert load_profile(path) == profile
    profile['country'] = 'Canada'
    save_profile(profile, path)
    assert load_profile(path)['country'] == 'Canada'
    with pytest.raises(ValueError):
        save_profile({**profile, 'country': ' '}, path)


def test_eligibility_rules():
    item = demo_opportunities()[1]
    today = date(2027, 1, 1)
    profile = dict(country='Pakistan', education_level='Undergraduate')
    assert eligibility(item, None, today)[0] == 'Profile needed'
    assert eligibility(item, profile, today)[0] == 'Potential match'
    assert eligibility(item, {**profile, 'country': 'Canada'}, today)[0] == 'Criteria mismatch'
    assert eligibility(item, {**profile, 'education_level': 'High school'}, today)[0] == 'Criteria mismatch'
    assert eligibility(item, profile, date(2028, 1, 1))[0] == 'Deadline passed'
    assert eligibility(item, profile, date(2027, 4, 30))[0] == 'Potential match'
