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
