"""Deterministic expanded synthetic fixture, separate from the legacy demo."""
from datetime import timedelta
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
    records=conn.execute('SELECT transaction_id,transaction_timestamp FROM core.transactions').fetchall()
    with conn.transaction():
        for row in records:
            seconds=int(row['transaction_id']) % 60
            conn.execute('UPDATE core.transactions SET transaction_timestamp=%s WHERE transaction_id=%s',
                (row['transaction_timestamp']+timedelta(seconds=seconds),row['transaction_id']))
