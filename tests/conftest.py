import os
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict
from psycopg.rows import dict_row

from aml.db import bootstrap
from aml.generate import demo_entities, transactions
from aml.ingest import ingest


@pytest.fixture(scope='session')
def database(tmp_path_factory):
    dsn = os.getenv('AML_TEST_DSN')
    if not dsn:
        pytest.skip('Set AML_TEST_DSN to a PostgreSQL role allowed to create a temporary test database')
    name = 'aml_test_' + uuid4().hex[:12]
    admin = psycopg.connect(dsn, autocommit=True)
    admin.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
    kwargs = conninfo_to_dict(dsn)
    kwargs['dbname'] = name
    conn = psycopg.connect(**kwargs, autocommit=True, row_factory=dict_row)
    directory = tmp_path_factory.mktemp('synthetic')
    try:
        bootstrap(conn)
        demo_entities(conn, directory, customers=100)
        transactions(conn, directory, per_account=20)
        assert ingest(conn, 'transactions', directory / 'transactions.csv')['rejected'] == 0
        yield conn, directory
    finally:
        conn.close()
        admin.execute(sql.SQL('DROP DATABASE {} WITH (FORCE)').format(sql.Identifier(name)))
        admin.close()
