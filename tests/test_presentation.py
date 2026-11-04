from datetime import date
from opportunityradar.presentation import card_html, short_description
from opportunityradar.ranking import quality_signals, sort_opportunities
from opportunityradar.discovery import build_query


def test_card_escapes_untrusted_data_and_clamps_summary():
    attack = '<img src=x onerror="alert(1)">'
    html = card_html(dict(title=attack, organization=attack, category=attack, summary=attack * 30))
    assert '<img' not in html and '&lt;img' in html
    assert len(short_description(attack * 30)) <= 180
    assert 'Unverified' in html
    assert 'Unknown' in html
    assert 'https://' not in html


def test_ranking_prefers_application_pages_without_claiming_verification():
    official = dict(title='Software internship applications open', source_url='https://school.edu/careers/apply', summary='Apply for research internship')
    guide = dict(title='Top 10 internship tips 2024', source_url='https://example.org/blog/tips', summary='internship guide')
    social = dict(title='Look at this', source_url='https://www.reddit.com/post', summary='unrelated post')
    assert quality_signals(official, date(2026, 11, 3))[0] > quality_signals(guide, date(2026, 11, 3))[0]
    assert sort_opportunities([social, guide, official])[0] == official
    assert 'May refer to an older or closed opportunity' in quality_signals(guide, date(2026, 11, 3))[1]
    assert 'verified' not in official
    assert quality_signals({'source_url': 'https://reddit.com.example.org/apply', 'title':'Internship'})[0] > quality_signals(social)[0]


def test_sort_handles_unknown_dates_and_newest_first():
    unknown = {'title': 'Zebra', 'deadline': 'bad', 'discovered_at': None}
    earlier = {'title': 'Alpha', 'deadline': '2027-01-01', 'discovered_at': '2026-11-01T10:00:00+00:00'}
    later = {'title': 'Beta', 'deadline': '2027-06-01', 'discovered_at': '2026-11-03T10:00:00+00:00'}
    items = [unknown, later, earlier]
    assert sort_opportunities(items, 'Deadline soonest') == [earlier, later, unknown]
    assert sort_opportunities(items, 'Recently discovered') == [later, earlier, unknown]
    assert sort_opportunities(items, 'Title A–Z') == [earlier, later, unknown]


def test_query_requests_original_pages_and_includes_keyword():
    query = build_query('CS internships', {'country': 'Pakistan'}, keyword='robotics')
    assert 'official organizer application page' in query
    assert 'Pakistan' in query and 'robotics' in query
