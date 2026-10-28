import json
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


def test_checked_in_snapshot_matches_reproducible_database(database):
    conn,_=database
    public=json.loads((Path(__file__).resolve().parents[1]/'web/network/data.json').read_text())
    assert public==build_snapshot(conn)
