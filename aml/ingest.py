"""Typed staging, SQL business validation, per-row quarantine and safe replay."""
import csv
import hashlib
from pathlib import Path
from uuid import uuid4

import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb

KEYS = {'customers': 'customer_number', 'accounts': 'account_number',
        'beneficiaries': 'beneficiary_account_number', 'transactions': 'transaction_id'}

VALIDATION = {
    'customers': """SELECT CASE WHEN date_of_birth > CURRENT_DATE OR annual_income < 0
        THEN 'invalid_birth_date_or_income' END AS reason FROM incoming""",
    'accounts': """SELECT CASE WHEN balance < -overdraft_limit OR overdraft_limit < 0
        OR opened_date > CURRENT_DATE OR closed_date < opened_date
        OR closed_date > CURRENT_DATE
        OR (account_status='CLOSED') IS DISTINCT FROM (closed_date IS NOT NULL)
        THEN 'invalid_account_dates_or_balance' END AS reason FROM incoming""",
    'beneficiaries': 'SELECT NULL::text AS reason FROM incoming',
    'transactions': """SELECT CASE
        WHEN t.transaction_timestamp IS NULL OR t.transaction_timestamp > CURRENT_TIMESTAMP
            THEN 'invalid_timestamp'
        WHEN t.exchange_rate IS NULL OR t.exchange_rate <= 0 OR t.exchange_rate::text IN ('NaN','Infinity')
            OR t.amount::text IN ('NaN','Infinity') THEN 'invalid_amount_or_fx'
        WHEN a.account_status <> 'ACTIVE' OR c.customer_status <> 'ACTIVE' THEN 'inactive_account_or_customer'
        WHEN t.currency_id <> a.currency_id THEN 'currency_mismatch'
        WHEN t.transaction_timestamp::date < a.opened_date THEN 'before_account_opened'
        WHEN t.beneficiary_id IS NOT NULL AND
             (b.customer_id <> a.customer_id OR b.beneficiary_status <> 'ACTIVE'
              OR t.country_id <> b.beneficiary_country_id) THEN 'invalid_beneficiary_relationship'
        END AS reason
        FROM incoming t LEFT JOIN core.accounts a USING(account_id)
        LEFT JOIN core.customers c ON c.customer_id=a.customer_id
        LEFT JOIN core.beneficiaries b USING(beneficiary_id)"""
}


def ingest(conn, entity, path):
    if entity not in KEYS:
        raise ValueError('Unknown entity')
    path = Path(path)
    batch = uuid4()
    counts = {'accepted': 0, 'rejected': 0, 'replayed': 0}
    with path.open(newline='', encoding='utf-8') as source, conn.transaction():
        # Serialize ingestions to make duplicate conflict decisions deterministic.
        conn.execute('SELECT pg_advisory_xact_lock(7182302)')
        reader = csv.DictReader(source)
        columns = reader.fieldnames or []
        metadata = conn.execute('''SELECT column_name, is_nullable, column_default
            FROM information_schema.columns WHERE table_schema='core' AND table_name=%s''', (entity,)).fetchall()
        allowed = {r['column_name'] for r in metadata} - {'created_at', 'updated_at'}
        required = {r['column_name'] for r in metadata if r['is_nullable'] == 'NO' and r['column_default'] is None}
        required.add(KEYS[entity])
        if len(set(columns)) != len(columns) or not required <= set(columns) or not set(columns) <= allowed:
            raise ValueError(f'Invalid CSV header for {entity}; required: {sorted(required)}')
        names = sql.SQL(',').join(map(sql.Identifier, columns))
        table = sql.Identifier('core', entity)
        key = sql.Identifier(KEYS[entity])
        with path.open('rb') as binary_source:
            digest = hashlib.file_digest(binary_source, 'sha256').hexdigest()
        conn.execute('INSERT INTO staging.ingestion_batches(batch_id,entity,source_name,source_sha256) VALUES (%s,%s,%s,%s)',
                     (batch, entity, path.name, digest))
        conn.execute(sql.SQL('CREATE TEMP TABLE incoming (LIKE {} INCLUDING DEFAULTS) ON COMMIT DROP').format(table))
        for number, raw in enumerate(reader, 2):
            status, reason = 'ACCEPTED', None
            try:
                with conn.transaction():
                    if None in raw or any(v is None for v in raw.values()):
                        raise ValueError('column_count_mismatch')
                    conn.execute('TRUNCATE incoming')
                    conn.execute(sql.SQL('INSERT INTO incoming ({}) VALUES ({})').format(
                        names, sql.SQL(',').join(sql.Placeholder() for _ in columns)),
                        [v if v != '' else None for v in raw.values()])
                    # Compare typed values, not formatting (e.g. 1.00 vs 1).
                    existing = conn.execute(sql.SQL('''SELECT ({}) IS NOT DISTINCT FROM ({}) AS identical
                        FROM {} c JOIN incoming i ON c.{}=i.{}''').format(
                        sql.SQL(',').join(sql.Identifier('c', c) for c in columns),
                        sql.SQL(',').join(sql.Identifier('i', c) for c in columns), table, key, key)).fetchone()
                    if existing:
                        if not existing['identical']:
                            raise ValueError('conflicting_duplicate_key')
                        status = 'REPLAYED'
                    else:
                        reason = conn.execute(VALIDATION[entity]).fetchone()['reason']
                        if reason:
                            raise ValueError(reason)
                        conn.execute(sql.SQL('INSERT INTO {} ({}) SELECT {} FROM incoming').format(table, names, names))
            except (psycopg.DataError, psycopg.IntegrityError, ValueError) as exc:
                status = 'REJECTED'
                # Store error category only: database error detail may contain personal data.
                reason = str(exc) if isinstance(exc, ValueError) else f'{exc.sqlstate}:{type(exc).__name__}'
            payload = {str(k): v for k, v in raw.items()}
            conn.execute('INSERT INTO staging.ingestion_rows VALUES (%s,%s,%s,%s,%s)',
                         (batch, number, Jsonb(payload), status, reason))
            counts[status.lower()] += 1
        conn.execute('''UPDATE staging.ingestion_batches SET finished_at=now(),accepted=%s,rejected=%s,replayed=%s
                        WHERE batch_id=%s''', (*counts.values(), batch))
    return {'batch_id': str(batch), **counts}
