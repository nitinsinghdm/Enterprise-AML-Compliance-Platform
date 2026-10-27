import os

import pandas as pd
import pytest

from aml.export import export


@pytest.mark.skipif(os.getenv('AML_TEST_SPARK') != '1', reason='Set AML_TEST_SPARK=1 with Java 17 and Spark installed')
def test_spark_matches_postgres_and_rejects_duplicates(database, tmp_path):
    from aml.spark import run
    from pyspark.sql import SparkSession
    conn, _ = database
    export(conn, tmp_path / 'export')
    source = tmp_path / 'export/transaction_facts.csv'
    result = run(source, tmp_path / 'spark')
    expected = pd.read_csv(tmp_path / 'export/dashboard_daily.csv')
    assert result['silver_rows'] == 2110
    assert result['gold_rows'] == len(expected)
    spark = SparkSession.builder.master('local[2]').getOrCreate()
    try:
        actual = spark.read.parquet(str(tmp_path / 'spark/gold')).toPandas()
        keys = ['transaction_date', 'destination_country', 'channel']
        actual['transaction_date'] = actual.transaction_date.astype(str)
        actual['completed_amount_eur'] = actual.completed_amount_eur.astype(float)
        pd.testing.assert_frame_equal(actual.sort_values(keys).reset_index(drop=True),
                                      expected.sort_values(keys).reset_index(drop=True), check_dtype=False)
    finally:
        spark.stop()
    # Replaying the snapshot must not append duplicate output.
    assert run(source, tmp_path / 'spark') == result
    lines = source.read_text().splitlines()
    source.write_text('\n'.join(lines + [lines[1]]) + '\n')
    with pytest.raises(ValueError, match='Duplicate'):
        run(source, tmp_path / 'spark')
