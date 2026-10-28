import json
from uuid import uuid4
import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from aml.network_fixture import populate
from pathlib import Path
from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from aml.network import build_snapshot, evidence_for, write_snapshot


def row(n, minute, amount='100', direction='OUTGOING', status='COMPLETED'):
    return dict(transaction_id=str(n), transaction_timestamp=datetime(2026,1,1)+timedelta(minutes=minute),
        transaction_date=date(2026,1,1), amount_eur=Decimal(amount), transaction_status=status,
        transaction_direction=direction, transaction_type_name='TRANSFER', cross_border=False, country_risk='LOW')


def test_velocity_includes_ties_boundary_and_excludes_failed():
    rows = [row(i, 0) for i in range(9)] + [row(9,60), row(10,61,status='FAILED')]
    counted, support, count = evidence_for(rows,'VELOCITY',date(2026,1,1))
    assert [r['transaction_id'] for r in counted] == ['9']
    assert len(support) == count == 10
    rows[9]['transaction_timestamp'] += timedelta(seconds=1)
    assert evidence_for(rows,'VELOCITY',date(2026,1,1))[0] == []


def test_rapid_movement_support_is_not_double_counted():
    rows = [row(1,0,'10000','INCOMING'),row(2,1,'10000','INCOMING'),row(3,20,'9500')]
    counted,support,count=evidence_for(rows,'RAPID_MOVEMENT',date(2026,1,1))
    assert count==1 and len(support)==3 and sum(r['amount_eur'] for r in counted)==9500


def test_public_export_requires_confirmation(tmp_path):
    with pytest.raises(ValueError,match='synthetic'):
        write_snapshot(None,tmp_path/'data.json')


def test_network_reconciles_sql_and_does_not_invent_links(database):
    conn,_=database
    data=build_snapshot(conn)
    assert len(data['transactions'])==2110
    assert len(data['alerts'])==30
    assert {a['rule'] for a in data['alerts']}=={'STRUCTURING','VELOCITY','RAPID_MOVEMENT','HIGH_RISK_CORRIDOR'}
    ids={t['id'] for t in data['transactions']}
    for alert in data['alerts']:
        assert set(alert['counted']) <= set(alert['evidence']) <= ids
        assert all(t['status']=='COMPLETED' for t in data['transactions'] if t['id'] in alert['evidence'])
    assert all(t['beneficiary'] is None for t in data['transactions'] if t['direction']=='INCOMING')
    assert all(set(t)=={'id','account','beneficiary','timestamp','day','amount','direction','kind','country','status','channel'} for t in data['transactions'])


def test_checked_in_snapshot_matches_reproducible_database(expanded_network_database):
    conn=expanded_network_database
    public=json.loads((Path(__file__).resolve().parents[1]/'web/network/data.json').read_text())
    assert public==build_snapshot(conn)


@pytest.fixture(scope='module')
def expanded_network_database(database, tmp_path_factory):
    admin,_=database
    name='aml_network_test_'+uuid4().hex[:10]
    admin.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
    params=admin.info.get_parameters();params['dbname']=name
    try:
        with psycopg.connect(**params,autocommit=True,row_factory=dict_row) as conn:
            populate(conn,tmp_path_factory.mktemp('expanded-network'))
            yield conn
    finally:
        admin.execute(sql.SQL('DROP DATABASE {} WITH (FORCE)').format(sql.Identifier(name)))


def test_alert_versions_never_use_future_evidence(database):
    conn,_=database
    data=build_snapshot(conn)
    records={t['id']:t for t in data['transactions']}
    latest={}
    for event in data['alert_events']:
        assert all(records[key]['timestamp']<=event['timestamp'] for key in event['evidence'])
        assert event['first_detected']<=event['timestamp']
        latest[event['id']]=event
    for alert in data['alerts']:
        assert all(latest[alert['id']][key]==value for key,value in alert.items())


def test_event_prefixes_reconcile_to_sql_without_future_rows(database):
    conn,_=database
    data=build_snapshot(conn)
    first={}
    for event in data['alert_events']:
        first.setdefault(event['rule'],event)
    times=[datetime.fromisoformat(e['timestamp'].removesuffix('Z')) for e in first.values()]
    times+=[min(times)-timedelta(seconds=1),max(datetime.fromisoformat(e['timestamp'].removesuffix('Z')) for e in data['alert_events'])]
    view=conn.execute("SELECT pg_get_viewdef('analytics.aml_alerts'::regclass, true) AS definition").fetchone()['definition']
    view=view.replace('FROM analytics.transaction_facts', 'FROM (SELECT * FROM analytics.transaction_facts WHERE transaction_timestamp <= %(at)s) AS transaction_facts')
    account_ids=[str(r['account_id']) for r in conn.execute('SELECT DISTINCT account_id FROM analytics.transaction_facts ORDER BY account_id')]
    labels={value:f'AC-{i:03}' for i,value in enumerate(account_ids,1)}
    for at in times:
        expected={(labels[str(r['account_id'])],r['transaction_date'].isoformat(),r['rule_code']):(r['evidence_count'],float(r['amount_eur'])) for r in conn.execute(view,{'at':at})}
        latest={}
        for event in data['alert_events']:
            if event['timestamp']<=at.isoformat()+'Z':
                latest[event['id']]=event
        actual={(e['account'],e['day'],e['rule']):(e['count'],e['amount']) for e in latest.values()}
        assert actual==expected
