"""Deterministic synthetic fixtures and behavioral transactions against actual reference IDs."""
import csv
import random
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from .ingest import ingest


def uid(value):
    return str(uuid5(NAMESPACE_URL, 'northstar-demo/' + str(value)))


def write_csv(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError('Cannot write an empty dataset')
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def demo_entities(conn, output, customers=200, seed=42):
    """Small reproducible alternative to the preserved original 10K/12K/18K scripts."""
    if customers < 20:
        raise ValueError('Demo requires at least 20 customers')
    rng = random.Random(seed)
    country = conn.execute("SELECT country_id FROM reference.countries WHERE iso_code='DE'").fetchone()['country_id']
    currency = conn.execute("SELECT currency_id FROM reference.currencies WHERE currency_code='EUR'").fetchone()['currency_id']
    branch = conn.execute('SELECT branch_id FROM reference.branches ORDER BY branch_id LIMIT 1').fetchone()['branch_id']
    data = {'customers': [], 'accounts': [], 'beneficiaries': []}
    for i in range(customers):
        customer, account = uid(f'{seed}/customer/{i}'), uid(f'{seed}/account/{i}')
        data['customers'].append(dict(customer_id=customer, customer_number=f'D{seed}-{i:08}',
            first_name='Synthetic', last_name=f'Customer{i}', date_of_birth='1980-01-01',
            nationality_id=country, residence_country_id=country, occupation='Employee',
            annual_income=rng.randint(25000, 120000), source_of_funds='SALARY', pep_flag=i % 31 == 0,
            customer_risk_level='LOW', customer_status='ACTIVE'))
        data['accounts'].append(dict(account_id=account, account_number=f'D{seed}-{i:08}', customer_id=customer,
            branch_id=branch, currency_id=currency, iban=f'DEMO{seed:06}{i:020}', account_type='CURRENT',
            account_status='ACTIVE', opened_date='2020-01-01', closed_date='', balance=20000,
            overdraft_limit=1000, interest_rate=0))
        data['beneficiaries'].append(dict(beneficiary_id=uid(f'{seed}/beneficiary/{i}'), customer_id=customer,
            beneficiary_name=f'Synthetic Payee {i}', beneficiary_account_number=f'DBEN{seed}-{i:08}',
            beneficiary_bank_name='Demo Bank', beneficiary_country_id=country, beneficiary_status='ACTIVE'))
    results = {}
    for entity, rows in data.items():
        path = Path(output) / f'{entity}.csv'
        write_csv(path, rows)
        results[entity] = ingest(conn, entity, path)
        if results[entity]['rejected']:
            raise ValueError(f'Demo {entity} ingestion rejected rows; inspect staging.ingestion_rows')
    return results


def transactions(conn, output, seed=42, per_account=30, start='2026-01-01'):
    if per_account < 1:
        raise ValueError('per_account must be positive')
    start = datetime.fromisoformat(start)
    if start.tzinfo or start + timedelta(days=30) > datetime.now():
        raise ValueError('Use a timezone-naive UTC start at least 30 days in the past')
    rng = random.Random(seed)
    accounts = conn.execute('''SELECT a.*, c.residence_country_id FROM core.accounts a
        JOIN core.customers c USING(customer_id) WHERE a.account_status='ACTIVE'
        AND c.customer_status='ACTIVE' AND a.opened_date <= %s ORDER BY a.account_id''', (start.date(),)).fetchall()
    if len(accounts) < 4:
        raise ValueError('At least four eligible active accounts are required')
    types = {r['transaction_type_name']: r['transaction_type_id'] for r in conn.execute('SELECT * FROM reference.transaction_types')}
    currencies = {r['currency_id']: r['currency_code'] for r in conn.execute('SELECT * FROM reference.currencies')}
    # Fixed synthetic EUR per unit rates: reproducibility, not market data.
    rates = dict(EUR='1', USD='.92', GBP='1.17', CHF='1.04', INR='.011', JPY='.0062',
                 CNY='.128', CAD='.68', AUD='.61', AED='.25', PLN='.23', SEK='.089')
    high = [r['country_id'] for r in conn.execute("SELECT country_id FROM reference.countries WHERE risk_rating IN ('HIGH','CRITICAL') ORDER BY country_id")]
    if not high or any(currencies[a['currency_id']] not in rates for a in accounts):
        raise ValueError('Missing high-risk reference country or synthetic FX rate')
    payees = {}
    for b in conn.execute("SELECT * FROM core.beneficiaries WHERE beneficiary_status='ACTIVE' ORDER BY beneficiary_id"):
        payees.setdefault(b['customer_id'], []).append(b)
    rows, labels = [], []
    customer_ids = sorted({str(a['customer_id']) for a in accounts})
    # Assign at customer level, so customers cannot cross evaluation groups.
    scenarios = {c: ['structuring', 'velocity', 'high_risk_corridor', 'rapid_movement'][i % 4]
                 for i, c in enumerate(customer_ids) if i % 5 == 0}

    def add(a, at, eur, kind='CARD_PAYMENT', direction='OUTGOING', channel='MOBILE', scenario=None, country=None, status='COMPLETED'):
        rate = Decimal(rates[currencies[a['currency_id']]])
        row = dict(transaction_id=uid(f'{seed}/{start.isoformat()}/{len(rows)}'), account_id=str(a['account_id']),
            beneficiary_id='', transaction_type_id=types[kind], currency_id=a['currency_id'], exchange_rate=str(rate),
            country_id=country or a['residence_country_id'], merchant_category_id='',
            amount=str((Decimal(str(eur)) / rate).quantize(Decimal('.01'))), transaction_direction=direction,
            channel=channel, payment_reference='Synthetic banking activity', transaction_status=status,
            transaction_timestamp=at.isoformat(sep=' '))
        if kind == 'TRANSFER' and payees.get(a['customer_id']) and country is None:
            b = rng.choice(payees[a['customer_id']])
            row.update(beneficiary_id=str(b['beneficiary_id']), country_id=b['beneficiary_country_id'])
        rows.append(row)
        labels.append(dict(transaction_id=row['transaction_id'], customer_id=str(a['customer_id']),
                           scenario=scenario or 'baseline', is_suspicious=int(scenario is not None)))

    for a in accounts:
        for j in range(per_account):
            at = start + timedelta(days=rng.randrange(30), hours=rng.randrange(8, 21), minutes=rng.randrange(60))
            kind = rng.choices(['CARD_PAYMENT', 'TRANSFER', 'CASH_DEPOSIT', 'DEPOSIT'], [65, 20, 5, 10])[0]
            incoming = kind in ('CASH_DEPOSIT', 'DEPOSIT')
            add(a, at, round(min(rng.lognormvariate(4.8, 1.1), 5000), 2), kind,
                'INCOMING' if incoming else 'OUTGOING', 'BRANCH' if kind == 'CASH_DEPOSIT' else 'MOBILE',
                status=rng.choices(['COMPLETED', 'FAILED', 'PENDING'], [96, 2, 2])[0])
        scenario = scenarios.get(str(a['customer_id']))
        base = start + timedelta(days=15, hours=10)
        if scenario == 'structuring':
            for j in range(5):
                add(a, base + timedelta(minutes=j*30), rng.randint(9000, 9800), 'CASH_DEPOSIT', 'INCOMING', 'BRANCH', scenario)
        elif scenario == 'velocity':
            for j in range(12):
                add(a, base + timedelta(minutes=j*2), rng.randint(300, 800), 'TRANSFER', scenario=scenario)
        elif scenario == 'high_risk_corridor':
            for j in range(3):
                add(a, base + timedelta(days=j), rng.randint(12000, 25000), 'INTERNATIONAL_TRANSFER',
                    channel='SWIFT', scenario=scenario, country=rng.choice(high))
        elif scenario == 'rapid_movement':
            add(a, base, 20000, 'DEPOSIT', 'INCOMING', scenario=scenario)
            add(a, base + timedelta(minutes=20), 19000, 'TRANSFER', scenario=scenario)
    output = Path(output)
    write_csv(output / 'transactions.csv', rows)
    write_csv(output / 'scenario_labels.csv', labels)
    return {'transactions': len(rows), 'scenario_transactions': sum(x['is_suspicious'] for x in labels), 'seed': seed}
