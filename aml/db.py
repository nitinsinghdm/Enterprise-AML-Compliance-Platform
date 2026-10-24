"""Database access and non-destructive, checksum-tracked migrations."""
import hashlib
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parents[1]


def connect():
    load_dotenv(ROOT / '.env', override=False)
    # Empty DSN uses standard PGHOST/PGPORT/PGDATABASE/PGUSER/PGPASSWORD.
    return psycopg.connect(os.getenv('DATABASE_URL', ''), row_factory=dict_row, autocommit=True)


def bootstrap(conn):
    """Install preserved schema; never execute the legacy destructive TRUNCATE seeds."""
    paths = [ROOT / 'sql/setup/02_create_schema.sql',
             ROOT / 'sql/setup/03_create_extensions.sql']
    paths += sorted((ROOT / 'sql/schema').glob('*.sql'))
    paths += sorted((ROOT / 'sql/staging').glob('*.sql'))
    paths += sorted((ROOT / 'sql/migrations').glob('*.sql'))
    with conn.transaction():
        conn.execute('SELECT pg_advisory_xact_lock(7182301)')
        conn.execute('CREATE SCHEMA IF NOT EXISTS compliance')
        conn.execute('''CREATE TABLE IF NOT EXISTS compliance.schema_migrations
                     (path TEXT PRIMARY KEY, sha256 TEXT NOT NULL, applied_at TIMESTAMPTZ DEFAULT now())''')
        for path in paths:
            source = path.read_text()
            digest = hashlib.sha256(source.encode()).hexdigest()
            key = str(path.relative_to(ROOT))
            existing = conn.execute('SELECT sha256 FROM compliance.schema_migrations WHERE path=%s', (key,)).fetchone()
            if existing:
                if existing['sha256'] != digest:
                    raise ValueError(f'Applied migration changed: {key}; add a new migration instead')
                continue
            conn.execute(source)
            conn.execute('INSERT INTO compliance.schema_migrations(path, sha256) VALUES (%s,%s)', (key, digest))
        # Seed only a completely empty reference database. Partial installations need repair.
        tables = ['countries', 'currencies', 'branches', 'transaction_types', 'merchant_categories']
        counts = [conn.execute(f'SELECT count(*) AS n FROM reference.{t}').fetchone()['n'] for t in tables]
        if not any(counts):
            for path in sorted((ROOT / 'sql/seed').glob('*.sql')):
                source = path.read_text()
                # Preserve original seed files, but omit their TRUNCATE commands.
                conn.execute(source[source.index('INSERT INTO'):])
        elif not all(counts):
            raise ValueError('Partially seeded reference database; repair missing reference data before continuing')
        for path in sorted((ROOT / 'sql/analytics').glob('*.sql')):
            conn.execute(path.read_text())
