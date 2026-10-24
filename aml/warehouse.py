"""Explicit Snowflake mart contracts and transactional, repeatable MERGE loads."""
import csv
import os
import re
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
from .db import ROOT

# Export files, destination tables, natural keys and SQL types. No identifiers from CSV.
CONTRACTS = {
 'transaction_facts': ('FACT_TRANSACTIONS', ['transaction_id'],
   'transaction_id VARCHAR,customer_id VARCHAR,account_id VARCHAR,transaction_timestamp TIMESTAMP_NTZ,transaction_date DATE,amount NUMBER(18,2),currency_id INTEGER,amount_eur NUMBER(24,2),transaction_direction VARCHAR,channel VARCHAR,transaction_status VARCHAR,transaction_type_name VARCHAR,pep_flag BOOLEAN,customer_risk_level VARCHAR,destination_country VARCHAR,country_risk VARCHAR,cross_border BOOLEAN'),
 'customer_features': ('DIM_CUSTOMER_RISK_FEATURES', ['customer_id'],
   'customer_id VARCHAR,transaction_count INTEGER,total_amount_eur NUMBER(30,2),mean_amount_eur FLOAT,max_amount_eur NUMBER(24,2),cross_border_ratio FLOAT,high_risk_country_ratio FLOAT,near_threshold_cash_count INTEGER,max_daily_count INTEGER,pep_flag INTEGER'),
 'dashboard_daily': ('MART_DAILY_ACTIVITY', ['transaction_date', 'destination_country', 'channel'],
   'transaction_date DATE,destination_country VARCHAR,channel VARCHAR,transaction_count INTEGER,completed_count INTEGER,completed_amount_eur NUMBER(30,2),cross_border_count INTEGER'),
 'alerts': ('FACT_AML_ALERTS', ['customer_id', 'account_id', 'transaction_date', 'rule_code'],
   'customer_id VARCHAR,account_id VARCHAR,transaction_date DATE,rule_code VARCHAR,evidence_count INTEGER,amount_eur NUMBER(30,2)'),
 'customer_risk_scores': ('MART_CUSTOMER_RISK', ['customer_id', 'model_version'],
   'customer_id VARCHAR,risk_score FLOAT,risk_band VARCHAR,model_version VARCHAR,evaluation_split VARCHAR')
}


def columns(ddl):
    return [part.strip().split()[0] for part in re.split(r',\s*(?![^()]*\))', ddl)]


def config():
    load_dotenv(ROOT / '.env', override=False)
    required = ['ACCOUNT', 'USER', 'WAREHOUSE', 'DATABASE', 'SCHEMA', 'ROLE']
    missing = [f'SNOWFLAKE_{k}' for k in required if not os.getenv(f'SNOWFLAKE_{k}')]
    if missing:
        raise ValueError('Missing environment variables: ' + ', '.join(missing))
    cfg = {k.lower(): os.environ[f'SNOWFLAKE_{k}'] for k in required}
    for key in ('warehouse', 'database', 'schema', 'role'):
        if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_$]*', cfg[key]):
            raise ValueError(f'SNOWFLAKE_{key.upper()} must be a simple SQL identifier')
    auth = os.getenv('SNOWFLAKE_AUTHENTICATOR', 'externalbrowser')
    cfg['authenticator'] = auth
    if auth == 'snowflake':
        if not os.getenv('SNOWFLAKE_PASSWORD'):
            raise ValueError('SNOWFLAKE_PASSWORD is required for password authentication')
        cfg['password'] = os.environ['SNOWFLAKE_PASSWORD']
    elif auth == 'SNOWFLAKE_JWT':
        if not os.getenv('SNOWFLAKE_PRIVATE_KEY_FILE'):
            raise ValueError('SNOWFLAKE_PRIVATE_KEY_FILE is required')
        cfg['private_key_file'] = os.environ['SNOWFLAKE_PRIVATE_KEY_FILE']
        if os.getenv('SNOWFLAKE_PRIVATE_KEY_FILE_PWD'):
            cfg['private_key_file_pwd'] = os.environ['SNOWFLAKE_PRIVATE_KEY_FILE_PWD']
    elif auth != 'externalbrowser':
        raise ValueError('Supported authenticators: externalbrowser, SNOWFLAKE_JWT, snowflake')
    cfg.update(login_timeout=30, network_timeout=120)
    return cfg


def merge_sql(table, stage, keys, fields):
    table, stage = table.upper(), stage.upper()
    fields = [c.upper() for c in fields]
    keys = [c.upper() for c in keys]
    on = ' AND '.join(f't.{k}=s.{k}' for k in keys)
    updates = ','.join(f'{c}=s.{c}' for c in fields if c not in keys)
    return (f'MERGE INTO {table} t USING {stage} s ON {on} '
            f'WHEN MATCHED THEN UPDATE SET {updates} '
            f'WHEN NOT MATCHED THEN INSERT ({",".join(fields)}) VALUES ({",".join("s."+c for c in fields)})')


def load(directory, connection=None):
    owned = connection is None
    if owned:
        cfg = config()  # Validate before opening any connection.
        import snowflake.connector
        connection = snowflake.connector.connect(**cfg)
    results, stages = {}, []
    try:
        with connection.cursor() as cur:
            # Stage all inputs before BEGIN: Snowflake DDL implicitly commits.
            for name, (table, keys, ddl) in CONTRACTS.items():
                path = Path(directory) / f'{name}.csv'
                if not path.exists():
                    if name == 'customer_risk_scores':
                        continue
                    raise ValueError(f'Missing export: {path.name}')
                fields = columns(ddl)
                with path.open(newline='', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    if reader.fieldnames != fields:
                        raise ValueError(f'Unexpected columns in {path.name}')
                    rows, seen = [], set()
                    for row in reader:
                        key = tuple(row[k] for k in keys)
                        if any(not v for v in key) or key in seen:
                            raise ValueError(f'Empty or duplicate natural key in {path.name}')
                        seen.add(key)
                        if None in row or any(v is None for v in row.values()):
                            raise ValueError(f'Malformed row in {path.name}')
                        rows.append(tuple(v if v != '' else None for v in row.values()))
                stage = 'AML_STAGE_' + uuid4().hex.upper()
                cur.execute(f'CREATE TABLE IF NOT EXISTS {table} ({ddl})')
                cur.execute(f'CREATE TEMPORARY TABLE {stage} LIKE {table}')
                stages.append((table, stage, keys, fields))
                statement = f'INSERT INTO {stage} ({",".join(fields)}) VALUES ({",".join(["%s"]*len(fields))})'
                for i in range(0, len(rows), 1000):
                    cur.executemany(statement, rows[i:i+1000])
                results[name] = len(rows)
            cur.execute('BEGIN')
            try:
                for table, stage, keys, fields in stages:
                    cur.execute(merge_sql(table, stage, keys, fields))
                cur.execute('COMMIT')
            except Exception:
                cur.execute('ROLLBACK')
                raise
    finally:
        if owned:
            connection.close()
    return results
