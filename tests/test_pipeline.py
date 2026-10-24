import csv
from decimal import Decimal
from uuid import uuid4

import pandas as pd
import pytest

from aml.db import bootstrap
from aml.export import export
from aml.generate import transactions, write_csv
from aml.ingest import ingest
from aml.model import FEATURES, predict, train


def test_bootstrap_preserves_existing_data(database):
    conn, _ = database
    before = conn.execute('SELECT count(*) n FROM core.transactions').fetchone()['n']
    bootstrap(conn)
    assert conn.execute('SELECT count(*) n FROM core.transactions').fetchone()['n'] == before


def test_generation_deterministic_and_replay(database, tmp_path):
    conn, original = database
    transactions(conn, tmp_path, per_account=20)
    assert (tmp_path / 'transactions.csv').read_bytes() == (original / 'transactions.csv').read_bytes()
    result = ingest(conn, 'transactions', tmp_path / 'transactions.csv')
    assert result['replayed'] == 2110
    assert result['accepted'] == result['rejected'] == 0


@pytest.mark.parametrize('changes', [
    {'amount': '-1'}, {'amount': 'NaN'}, {'amount': 'not money'}, {'exchange_rate': '0'},
    {'exchange_rate': 'NaN'}, {'account_id': str(uuid4())}, {'transaction_direction': 'INVALID'},
    {'transaction_timestamp': '2099-01-01'}, {'transaction_timestamp': '2010-01-01'},
    {'transaction_timestamp': ''}, {'currency_id': '9999'}, {'country_id': '9999'},
    {'transaction_type_id': '9999'}, {'transaction_status': 'UNKNOWN'},
    {'beneficiary_id': str(uuid4())}])
def test_invalid_rows_quarantined_without_blocking_valid_row(database, tmp_path, changes):
    conn, directory = database
    with (directory / 'transactions.csv').open() as f:
        source = next(csv.DictReader(f))
    bad = {**source, 'transaction_id': str(uuid4()), **changes}
    good = {**source, 'transaction_id': str(uuid4())}
    # Roll back the entire test so subsequent feature tests see the original snapshot.
    with conn.transaction(force_rollback=True):
        path = tmp_path / 'mixed.csv'
        write_csv(path, [bad, good])
        result = ingest(conn, 'transactions', path)
        assert result['rejected'] == result['accepted'] == 1
        assert conn.execute('SELECT reason FROM staging.ingestion_rows WHERE batch_id=%s AND status=\'REJECTED\'',
                            (result['batch_id'],)).fetchone()['reason']


def test_conflicting_duplicate_does_not_overwrite(database, tmp_path):
    conn, directory = database
    with (directory / 'transactions.csv').open() as f:
        row = next(csv.DictReader(f))
    row['amount'] = '123456.78'
    write_csv(tmp_path / 'conflict.csv', [row])
    with conn.transaction(force_rollback=True):
        result = ingest(conn, 'transactions', tmp_path / 'conflict.csv')
        assert result['rejected'] == 1
        assert conn.execute('SELECT amount FROM core.transactions WHERE transaction_id=%s', (row['transaction_id'],)).fetchone()['amount'] != Decimal(row['amount'])


def test_business_relationship_validation(database, tmp_path):
    conn, directory = database
    with (directory / 'transactions.csv').open() as f:
        row = next(csv.DictReader(f))
    with conn.transaction(force_rollback=True):
        conn.execute("UPDATE core.accounts SET account_status='FROZEN' WHERE account_id=%s", (row['account_id'],))
        row['transaction_id'] = str(uuid4())
        write_csv(tmp_path / 'frozen.csv', [row])
        assert ingest(conn, 'transactions', tmp_path / 'frozen.csv')['rejected'] == 1


def test_all_scenarios_detected_and_noncompleted_excluded(database):
    conn, directory = database
    mapping = {'structuring': 'STRUCTURING', 'velocity': 'VELOCITY',
               'high_risk_corridor': 'HIGH_RISK_CORRIDOR', 'rapid_movement': 'RAPID_MOVEMENT'}
    labels = pd.read_csv(directory / 'scenario_labels.csv')
    alerts = conn.execute('SELECT DISTINCT customer_id,rule_code FROM analytics.aml_alerts').fetchall()
    actual = {(str(a['customer_id']), a['rule_code']) for a in alerts}
    expected = {(r.customer_id, mapping[r.scenario]) for r in labels.itertuples() if r.scenario != 'baseline'}
    assert expected <= actual
    with conn.transaction(force_rollback=True):
        conn.execute("UPDATE core.transactions SET transaction_status='FAILED'")
        assert conn.execute('SELECT count(*) n FROM analytics.aml_alerts').fetchone()['n'] == 0
        assert conn.execute('SELECT sum(transaction_count) n FROM analytics.customer_features').fetchone()['n'] == 0


def test_export_reconciles_and_model_holdout(database, tmp_path):
    conn, directory = database
    report = export(conn, tmp_path)
    facts = pd.read_csv(tmp_path / 'transaction_facts.csv')
    daily = pd.read_csv(tmp_path / 'dashboard_daily.csv')
    assert report['datasets']['transaction_facts']['rows'] == int(daily.transaction_count.sum())
    assert abs(daily.completed_amount_eur.sum() - facts.loc[facts.transaction_status == 'COMPLETED', 'amount_eur'].sum()) < .01
    metrics = train(tmp_path / 'customer_features.csv', directory / 'scenario_labels.csv', tmp_path)
    assert metrics['train_customers'] == 75 and metrics['test_customers'] == 25
    scores = pd.read_csv(tmp_path / 'customer_risk_scores.csv')
    assert len(scores) == 100 and scores.customer_id.is_unique
    assert scores.risk_score.between(0, 100).all()
    assert not {'customer_id', 'scenario', 'is_suspicious', 'target'} & set(FEATURES)
    predict(tmp_path / 'customer_features.csv', tmp_path / 'risk_model.joblib', tmp_path / 'predictions.csv')
    assert pd.read_csv(tmp_path / 'predictions.csv').risk_score.equals(scores.risk_score)


def test_bad_header_rejected_before_batch(database, tmp_path):
    conn, _ = database
    path = tmp_path / 'bad.csv'
    path.write_text('amount,amount\n1,2\n')
    with pytest.raises(ValueError, match='header'):
        ingest(conn, 'transactions', path)
