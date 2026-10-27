import csv
from unittest.mock import MagicMock

import pytest

from aml.warehouse import CONTRACTS, columns, config, load, merge_sql


def test_config_requires_credentials(monkeypatch):
    for key in ['ACCOUNT', 'USER', 'WAREHOUSE', 'DATABASE', 'SCHEMA', 'ROLE']:
        monkeypatch.setenv('SNOWFLAKE_' + key, '')
    with pytest.raises(ValueError, match='Missing environment'):
        config()


def test_warehouse_identifier_rejected(monkeypatch):
    for key in ['ACCOUNT', 'USER', 'WAREHOUSE', 'DATABASE', 'SCHEMA', 'ROLE']:
        monkeypatch.setenv('SNOWFLAKE_' + key, 'demo')
    monkeypatch.setenv('SNOWFLAKE_SCHEMA', 'x; DROP DATABASE x')
    with pytest.raises(ValueError, match='identifier'):
        config()


def prepare(directory):
    for name, (_, _, ddl) in CONTRACTS.items():
        fields = columns(ddl)
        with (directory / f'{name}.csv').open('w', newline='') as f:
            w = csv.writer(f)
            w.writerow(fields)
            w.writerow(['1'] * len(fields))


def test_all_merge_dml_in_one_transaction(tmp_path):
    prepare(tmp_path)
    conn = MagicMock()
    cur = conn.cursor.return_value.__enter__.return_value
    result = load(tmp_path, conn)
    statements = [c.args[0] for c in cur.execute.call_args_list]
    begin = statements.index('BEGIN')
    assert len(result) == 5
    assert all(s.startswith('MERGE') for s in statements[begin+1:-1])
    assert statements[-1] == 'COMMIT'
    assert len(cur.executemany.call_args_list) == 5


def test_merge_failure_rolls_back(tmp_path):
    prepare(tmp_path)
    conn = MagicMock()
    cur = conn.cursor.return_value.__enter__.return_value
    def execute(statement):
        if statement.startswith('MERGE'):
            raise RuntimeError('simulated network error')
    cur.execute.side_effect = execute
    with pytest.raises(RuntimeError):
        load(tmp_path, conn)
    assert cur.execute.call_args_list[-1].args[0] == 'ROLLBACK'


def test_duplicate_source_keys_fail_before_merge(tmp_path):
    prepare(tmp_path)
    path = tmp_path / 'transaction_facts.csv'
    path.write_text(path.read_text() + path.read_text().splitlines()[1] + '\n')
    conn = MagicMock()
    with pytest.raises(ValueError, match='duplicate'):
        load(tmp_path, conn)
    assert not any(c.args[0] == 'BEGIN' for c in conn.cursor.return_value.__enter__.return_value.execute.call_args_list)


def test_merge_has_stable_keys():
    statement = merge_sql('FACT', 'STAGE', ['id'], ['id', 'value'])
    assert 't.ID=s.ID' in statement and 'VALUE=s.VALUE' in statement
