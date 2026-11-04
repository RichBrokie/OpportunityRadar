from pathlib import Path
from streamlit.testing.v1 import AppTest
from opportunityradar.storage import load_profile

def cards(app):
    return [entry.value for entry in app.markdown if '<article class="opportunity-card">' in entry.value]


APP = Path(__file__).resolve().parents[1] / 'app.py'


def test_navigation_profile_and_filters(tmp_path, monkeypatch):
    db = tmp_path / 'ui.sqlite3'
    monkeypatch.setenv('OPPORTUNITYRADAR_DB', str(db))
    app = AppTest.from_file(str(APP)).run()
    assert not app.exception
    assert app.metric[0].value == '0'
    app.sidebar.radio[0].set_value('Your profile').run()
    app.button[0].click().run()
    assert app.error[0].value == 'Please enter your country.'
    app.text_input[0].set_value('Pakistan')
    app.multiselect[0].set_value(['Web development'])
    app.checkbox[0].check()
    app.button[0].click().run()
    assert not app.exception
    assert load_profile(db)['country'] == 'Pakistan'
    app.sidebar.radio[0].set_value('Opportunities').run()
    app.radio[0].set_value('Demo').run()
    assert len(cards(app)) == 2
    app.multiselect[0].set_value(['Internship']).run()
    assert len(cards(app)) == 1
    app.text_input[0].set_value('unmatched search').run()
    assert len(cards(app)) == 0
    assert any('No demo opportunities match' in message.value for message in app.info)
    assert not app.exception
    # A fresh session reads the persisted profile.
    fresh = AppTest.from_file(str(APP)).run()
    assert fresh.metric[2].value == 'Saved'


def test_discovery_is_explicit_and_survives_reruns(tmp_path, monkeypatch):
    from unittest.mock import MagicMock
    from opportunityradar import discovery
    monkeypatch.setenv('OPPORTUNITYRADAR_DB', str(tmp_path / 'discovery-ui.sqlite3'))
    monkeypatch.delenv('TAVILY_API_KEY', raising=False)
    client = MagicMock()
    client.search.return_value = {'results': [{'title': 'Student hackathon', 'url': 'https://example.org/event', 'content': None}]}
    monkeypatch.setattr(discovery, 'TavilyClient', MagicMock(return_value=client))
    app = AppTest.from_file(str(APP)).run()
    app.sidebar.radio[0].set_value('Opportunities').run()
    assert not app.exception
    client.search.assert_not_called()
    app.checkbox(key='browse_keyless').check()
    app.button[0].click().run()
    assert not app.exception
    assert client.search.call_count == 1
    assert not cards(app)  # Sparse snippets belong in review, never the likely list.
    app.radio(key='classification_filter').set_value('Needs review').run()
    assert len(cards(app)) == 1
    assert 'Student hackathon' in cards(app)[0]
    app.text_input(key='browse_filter').set_value('student').run()
    assert client.search.call_count == 1
    app.checkbox(key='browse_keyless').check()
    app.button[0].click().run()
    assert client.search.call_count == 1  # cache, including after filter rerun
    assert any('Cached search' in entry.value for entry in app.success)
    app.radio[0].set_value('Demo').run()
    assert not any('Student hackathon' in entry for entry in cards(app))


def test_dashboard_search_and_quick_navigation(tmp_path, monkeypatch):
    from unittest.mock import MagicMock
    from opportunityradar import discovery
    monkeypatch.setenv('OPPORTUNITYRADAR_DB', str(tmp_path / 'dashboard.sqlite3'))
    client = MagicMock()
    client.search.return_value = {'results': [{'title': 'Cedar research internship', 'url': 'https://example.org/apply', 'content': 'Research for students'}]}
    monkeypatch.setattr(discovery, 'TavilyClient', MagicMock(return_value=client))
    app = AppTest.from_file(str(APP)).run()
    client.search.assert_not_called()
    app.text_input(key='dashboard_query').set_value('robotics')
    app.checkbox(key='dashboard_keyless').check()
    app.button[0].click().run()
    assert not app.exception
    assert 'robotics' in client.search.call_args.kwargs['query']
    assert app.metric[0].value == '1'
    assert len(cards(app)) == 1
    app.button(key='quick_Internship').click().run()
    assert not app.exception
    assert app.sidebar.radio[0].value == 'Opportunities'
    assert app.multiselect(key='category_filter').value == ['Internship']
    assert len(cards(app)) == 1
    app.selectbox(key='sort_order').set_value('Title A–Z').run()
    assert client.search.call_count == 1


def test_triage_views_details_safe_rendering_and_demo_separation(tmp_path, monkeypatch):
    from opportunityradar.discovery import parse_result
    from opportunityradar.storage import initialize, save_discovered
    path = tmp_path / 'triage.sqlite3'
    monkeypatch.setenv('OPPORTUNITYRADAR_DB', str(path))
    initialize(path)
    raw = 'Organization: Cedar Lab\nLocation: remote\nFunding: funded\nEligibility: Undergraduates\nApply for a 12 week placement. Apply for a 12 week placement. <img src=x onerror="alert(1)">'
    rows = [
        ('Cedar internship', 'https://school.edu/apply', raw, 'Internship', '2026-11-01'),
        ('Orbit scholarship', 'https://school.edu/scholarships/orbit', 'Students may apply.', 'Scholarship', '2026-11-04'),
        ('Student hackathon', 'https://example.org/event', '', 'Hackathon', '2026-11-03'),
        ('Top 10 internships', 'https://example.org/blog', 'Read our guide.', 'Internship', '2026-11-02'),
    ]
    save_discovered([parse_result(dict(title=t, url=u, content=c), cat, when) for t, u, c, cat, when in rows], path)
    app = AppTest.from_file(str(APP)).run()
    assert len(cards(app)) == 2
    assert not any('Student hackathon' in card or 'Top 10' in card for card in cards(app))
    app.sidebar.radio[0].set_value('Opportunities').run()
    assert len(cards(app)) == 2
    app.selectbox(key='sort_order').set_value('Recently discovered').run()
    assert 'Orbit scholarship' in cards(app)[0]
    app.multiselect(key='category_filter').set_value(['Internship']).run()
    assert len(cards(app)) == 1
    card = cards(app)[0]
    assert card.count('Unverified') == 1
    assert card.count('Apply for a 12 week placement.') == 1
    assert 'https://' not in card and '<img' not in card
    assert 'Eligibility' not in card and 'Discovered:' not in card
    assert all(button.proto.label == 'View source' for button in app.get('link_button'))
    details = next(exp for exp in app.expander if exp.label == 'More details')
    assert any(entry.value == raw for entry in details.text)
    assert any(entry.value == 'https://school.edu/apply' for entry in details.text)
    app.multiselect(key='category_filter').set_value([]).run()
    app.radio(key='classification_filter').set_value('Needs review').run()
    assert len(cards(app)) == 1 and 'Student hackathon' in cards(app)[0]
    app.radio(key='classification_filter').set_value('Irrelevant').run()
    assert len(cards(app)) == 1 and 'Top 10' in cards(app)[0]
    app.radio(key='collection').set_value('Demo').run()
    assert len(cards(app)) == 6 and all('DEMO' in card for card in cards(app))
    assert not app.exception
