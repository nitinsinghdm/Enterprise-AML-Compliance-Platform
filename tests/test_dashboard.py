import json
from pathlib import Path

import pytest

pytest.importorskip('streamlit')
from streamlit.testing.v1 import AppTest
from aml.dashboard_data import PREVIEW, activity_metrics, filter_activity, load_snapshot

APP = Path(__file__).resolve().parents[1] / 'dashboard_app.py'


def test_preview_totals_and_no_personal_fields():
    snapshot = load_snapshot()
    daily = snapshot['frames']['dashboard_daily']
    assert activity_metrics(daily)['total'] == snapshot['manifest']['datasets']['transaction_facts']['rows']
    assert len(snapshot['frames']['alerts']) == 30
    raw = PREVIEW.read_text()
    assert not any(f'"{field}"' in raw for field in ('first_name','last_name','iban','payment_reference'))


def test_empty_filter_returns_zero_not_global_totals():
    daily = load_snapshot()['frames']['dashboard_daily']
    selected = filter_activity(daily, [], list(daily.channel.unique()), ())
    assert activity_metrics(selected) == {'total':0,'completed':0,'volume':0.,'completion_rate':0}


@pytest.mark.parametrize('page',['Overview','Alert explorer','Customer risk','Pipeline & guide'])
def test_every_page_renders_without_database(page):
    app = AppTest.from_file(str(APP),default_timeout=15).run()
    app.radio[0].set_value(page).run()
    assert not app.exception
    assert len(app.title) == 1
    assert app.selectbox(key='data_source').value == 'Bundled preview'


def test_overview_filter_changes_metrics():
    app = AppTest.from_file(str(APP),default_timeout=15).run()
    assert app.metric[0].value == '2,110'
    app.multiselect[0].set_value([]).run()
    assert app.metric[0].value == '0'
    assert not app.exception


def test_alert_empty_selection_and_holdout_filter():
    app = AppTest.from_file(str(APP),default_timeout=15).run()
    app.radio[0].set_value('Alert explorer').run()
    app.multiselect[0].set_value([]).run()
    assert app.metric[0].value == '0'
    assert not app.exception
    app.radio[0].set_value('Customer risk').run()
    app.selectbox(key='evaluation_group').set_value('holdout').run()
    assert app.metric[0].value == '25'
    assert not app.exception


def test_missing_and_tampered_local_export(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_snapshot('My local exports',tmp_path)
    (tmp_path/'manifest.json').write_text(json.dumps({'datasets':{'dashboard_daily':{'sha256':'wrong','rows':1}}}))
    (tmp_path/'dashboard_daily.csv').write_text('bad\n1\n')
    with pytest.raises(ValueError,match='differs from its manifest'):
        load_snapshot('My local exports',tmp_path)
