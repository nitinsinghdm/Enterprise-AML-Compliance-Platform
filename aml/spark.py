"""Validated PostgreSQL facts -> typed silver Parquet -> daily gold Parquet."""
from pathlib import Path


def run(source, output, master='local[2]'):
    from pyspark.sql import SparkSession, functions as F, types as T
    spark = (SparkSession.builder.master(master).appName('NorthStarAML')
             .config('spark.sql.session.timeZone', 'UTC').config('spark.sql.shuffle.partitions', '2').getOrCreate())
    try:
        schema = T.StructType([
            T.StructField('transaction_id', T.StringType()), T.StructField('customer_id', T.StringType()),
            T.StructField('account_id', T.StringType()), T.StructField('transaction_timestamp', T.TimestampType()),
            T.StructField('transaction_date', T.DateType()), T.StructField('amount', T.DecimalType(18, 2)),
            T.StructField('currency_id', T.IntegerType()), T.StructField('amount_eur', T.DecimalType(24, 2)),
            T.StructField('transaction_direction', T.StringType()), T.StructField('channel', T.StringType()),
            T.StructField('transaction_status', T.StringType()), T.StructField('transaction_type_name', T.StringType()),
            T.StructField('pep_flag', T.BooleanType()), T.StructField('customer_risk_level', T.StringType()),
            T.StructField('destination_country', T.StringType()), T.StructField('country_risk', T.StringType()),
            T.StructField('cross_border', T.BooleanType())])
        df = (spark.read.option('header', True).option('mode', 'FAILFAST')
              .option('enforceSchema', False).schema(schema).csv(str(source))).cache()
        invalid = df.filter(F.col('transaction_id').isNull() | F.col('customer_id').isNull()
                            | F.col('transaction_timestamp').isNull() | F.col('transaction_date').isNull()
                            | F.col('amount_eur').isNull() | (F.col('amount_eur') <= 0))
        if invalid.limit(1).count():
            raise ValueError('Invalid facts: expected validated export from PostgreSQL')
        if df.groupBy('transaction_id').count().filter('count > 1').limit(1).count():
            raise ValueError('Duplicate transaction IDs in snapshot')
        count = df.count()
        if count == 0:
            raise ValueError('Empty facts snapshot')
        out = Path(output)
        # Snapshot overwrite is idempotent; use a dedicated run directory, never the CSV source.
        if Path(source).resolve().is_relative_to(out.resolve()):
            raise ValueError('Output must not contain input')
        df.write.mode('overwrite').partitionBy('transaction_date').parquet(str(out / 'silver'))
        completed = F.col('transaction_status') == 'COMPLETED'
        gold = df.groupBy('transaction_date', 'destination_country', 'channel').agg(
            F.count('*').alias('transaction_count'),
            F.sum(F.when(completed, 1).otherwise(0)).alias('completed_count'),
            F.sum(F.when(completed, F.col('amount_eur')).otherwise(0)).alias('completed_amount_eur'),
            F.sum(F.when(completed & F.col('cross_border'), 1).otherwise(0)).alias('cross_border_count'))
        gold.write.mode('overwrite').parquet(str(out / 'gold'))
        gold_rows = gold.count()
        df.unpersist()
        return {'silver_rows': count, 'gold_rows': gold_rows}
    finally:
        spark.stop()
