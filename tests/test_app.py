from pathlib import Path
from streamlit.testing.v1 import AppTest
from opportunityradar.storage import load_profile

APP = Path(__file__).resolve().parents[1] / 'app.py'


def test_navigation_profile_and_filters(tmp_path, monkeypatch):
    db = tmp_path / 'ui.sqlite3'
    monkeypatch.setenv('OPPORTUNITYRADAR_DB', str(db))
    app = AppTest.from_file(str(APP)).run()
    assert not app.exception
    assert app.metric[0].value == '6'
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
    assert len(app.subheader) == 2
    app.multiselect[0].set_value(['Internship']).run()
    assert len(app.subheader) == 1
    app.text_input[0].set_value('unmatched search').run()
    assert len(app.subheader) == 0
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
    app.checkbox[0].check().run()
    app.button[0].click().run()
    assert not app.exception
    assert client.search.call_count == 1
    assert len(app.subheader) == 1
    assert app.subheader[0].value == 'Student hackathon'
    app.text_input[0].set_value('student').run()
    assert client.search.call_count == 1
    app.button[0].click().run()
    assert client.search.call_count == 1  # cache, including after filter rerun
    assert any('Cached search' in entry.value for entry in app.info)
    app.radio[0].set_value('Demo').run()
    assert not any(entry.value == 'Student hackathon' for entry in app.subheader)
