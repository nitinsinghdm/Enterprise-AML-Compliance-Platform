"""Read-only network snapshot with SQL-reconciled, transaction-level alert evidence.

This is an offline research export, not a streaming detector. Unknown counterparties
remain unknown; beneficiary identifiers never imply ownership by another core account.
"""
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal
import hashlib
import json
from pathlib import Path

VERSION = 'northstar-sql-v1'


def evidence_for(rows: list[dict], rule: str, day) -> tuple[list[dict], list[dict], int]:
    """Return counted rows, contextual rows, and the SQL-compatible evidence count."""
    completed = [r for r in rows if r['transaction_status'] == 'COMPLETED']
    current = [r for r in completed if r['transaction_date'] == day]
    support = {}
    counts = []
    if rule == 'STRUCTURING':
        counted = [r for r in current if r['transaction_type_name'] == 'CASH_DEPOSIT'
                   and r['transaction_direction'] == 'INCOMING'
                   and Decimal(8000) <= r['amount_eur'] < Decimal(10000)]
    elif rule == 'HIGH_RISK_CORRIDOR':
        counted = [r for r in current if r['cross_border'] and r['country_risk'] in ('HIGH', 'CRITICAL')
                   and r['amount_eur'] >= 10000]
    elif rule == 'VELOCITY':
        counted = []
        for r in current:
            window = [i for i in completed if r['transaction_timestamp'] - timedelta(hours=1)
                      <= i['transaction_timestamp'] <= r['transaction_timestamp']]
            if len(window) >= 10:
                counted.append(r)
                counts.append(len(window))
                support.update((str(i['transaction_id']), i) for i in window)
    elif rule == 'RAPID_MOVEMENT':
        counted = []
        for r in current:
            if r['transaction_direction'] != 'OUTGOING' or r['amount_eur'] < 9000:
                continue
            incoming = [i for i in completed if i['transaction_direction'] == 'INCOMING'
                        and r['transaction_timestamp'] - timedelta(hours=1) <= i['transaction_timestamp'] < r['transaction_timestamp']
                        and i['amount_eur'] * Decimal('.8') <= r['amount_eur'] <= i['amount_eur'] * Decimal('1.2')]
            if incoming:
                counted.append(r)
                support.update((str(i['transaction_id']), i) for i in incoming)
    else:
        raise ValueError(f'Unknown rule: {rule}')
    support.update((str(r['transaction_id']), r) for r in counted)
    return counted, sorted(support.values(), key=lambda r: (r['transaction_timestamp'], str(r['transaction_id']))), max(counts) if counts else len(counted)


def build_snapshot(conn) -> dict:
    with conn.transaction():
        conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')
        rows = conn.execute('''SELECT f.*, t.beneficiary_id FROM analytics.transaction_facts f
            JOIN core.transactions t USING(transaction_id)
            ORDER BY f.transaction_timestamp,f.transaction_id''').fetchall()
        alerts = conn.execute('SELECT * FROM analytics.aml_alerts ORDER BY transaction_date,account_id,rule_code').fetchall()
    grouped = defaultdict(list)
    for row in rows:
        grouped[str(row['account_id'])].append(row)
    accounts = {key: f'AC-{n:03}' for n, key in enumerate(sorted(grouped), 1)}
    customers = {key: f'CU-{n:03}' for n, key in enumerate(sorted({str(r['customer_id']) for r in rows}), 1)}
    beneficiaries = {key: f'EX-{n:03}' for n, key in enumerate(sorted({str(r['beneficiary_id']) for r in rows if r['beneficiary_id']}), 1)}
    transactions = {str(r['transaction_id']): f'TX-{n:05}' for n, r in enumerate(rows, 1)}
    output_alerts = []
    for alert in alerts:
        account = str(alert['account_id'])
        counted, support, count = evidence_for(grouped[account], alert['rule_code'], alert['transaction_date'])
        amount = sum((r['amount_eur'] for r in counted), Decimal(0))
        if count != alert['evidence_count'] or amount != alert['amount_eur']:
            raise ValueError('Evidence does not reconcile with SQL; refusing to export')
        identity = f"{account}/{alert['transaction_date']}/{alert['rule_code']}"
        output_alerts.append(dict(id='AL-'+hashlib.sha256(identity.encode()).hexdigest()[:12],
            account=accounts[account], day=alert['transaction_date'].isoformat(), rule=alert['rule_code'],
            amount=float(amount), count=count, evidence=[transactions[str(r['transaction_id'])] for r in support],
            counted=[transactions[str(r['transaction_id'])] for r in counted], version=VERSION))
    return dict(schema_version=1, rules_version=VERSION, synthetic=True,
        provenance='NorthStar synthetic banking records. Account and beneficiary labels are local snapshot aliases, not real identities. Not live banking.',
        accounts=[dict(id=accounts[key], customer=customers[str(grouped[key][0]['customer_id'])]) for key in sorted(grouped)],
        transactions=[dict(id=transactions[str(r['transaction_id'])], account=accounts[str(r['account_id'])],
            beneficiary=beneficiaries.get(str(r['beneficiary_id'])) if r['transaction_direction'] == 'OUTGOING' else None,
            timestamp=r['transaction_timestamp'].isoformat()+'Z', day=r['transaction_date'].isoformat(),
            amount=float(r['amount_eur']), direction=r['transaction_direction'], kind=r['transaction_type_name'],
            country=r['destination_country'], status=r['transaction_status'], channel=r['channel']) for r in rows],
        alerts=output_alerts)


def write_snapshot(conn, path: Path, *, synthetic_data_confirmed: bool = False) -> dict:
    if not synthetic_data_confirmed:
        raise ValueError('Public export requires explicit confirmation of synthetic data')
    data = build_snapshot(conn)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, separators=(',', ':')))
    return {'transactions': len(data['transactions']), 'alerts': len(data['alerts'])}
