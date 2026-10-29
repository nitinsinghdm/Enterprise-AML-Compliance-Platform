"""Deterministic expanded synthetic fixture, separate from the legacy demo."""
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from .db import bootstrap
from .generate import demo_entities, transactions
from .ingest import ingest

CUSTOMERS = 250
PER_ACCOUNT = 40


def populate(conn, directory: Path) -> None:
    """Populate an EMPTY disposable database; never call against user data."""
    bootstrap(conn)
    if conn.execute('SELECT count(*) AS n FROM core.customers').fetchone()['n']:
        raise ValueError('Network fixture requires an empty disposable database')
    demo_entities(conn, directory, customers=CUSTOMERS)
    transactions(conn, directory, per_account=PER_ACCOUNT)
    result=ingest(conn, 'transactions', directory/'transactions.csv')
    if result['rejected']:
        raise ValueError('Fixture ingestion rejected records')
    # Seconds matter in playback. Preserve original generator logic and only add
    # deterministic second offsets inside this isolated fixture.
    records=conn.execute('SELECT transaction_id,transaction_timestamp,account_id,amount FROM core.transactions').fetchall()
    currencies={row['currency_code']:row['currency_id'] for row in conn.execute('SELECT currency_code,currency_id FROM reference.currencies')}
    with conn.transaction():
        for row in records:
            identity=int(row['transaction_id'])
            seconds=identity % 60
            # Fixed demonstration FX only. Preserve each original EUR comparison
            # to the cent, keeping alert evidence unchanged while varying source currency.
            code,rate='EUR',Decimal('1')
            account_bucket=int(row['account_id']) % 3
            if account_bucket == 1:
                code,rate='USD',Decimal('.8')
            elif account_bucket == 2:
                code,rate='GBP',Decimal('.9')
            original=(row['amount']/rate).quantize(Decimal('.01'))
            if (original*rate).quantize(Decimal('.01')) != row['amount']:
                raise ValueError('Fixture FX must preserve the EUR comparison amount')
            conn.execute('UPDATE core.accounts SET currency_id=%s WHERE account_id=%s',(currencies[code],row['account_id']))
            conn.execute('UPDATE core.transactions SET currency_id=%s,amount=%s,exchange_rate=%s WHERE transaction_id=%s',
                (currencies[code],original,rate,row['transaction_id']))
            conn.execute('UPDATE core.transactions SET transaction_timestamp=%s WHERE transaction_id=%s',
                (row['transaction_timestamp']+timedelta(seconds=seconds),row['transaction_id']))
