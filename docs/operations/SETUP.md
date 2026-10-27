# Full pipeline setup

A runnable synthetic banking and anti-money-laundering analytics project using **PostgreSQL, Python, SQL, PySpark, Snowflake, scikit-learn and Looker Studio**. It extends the original NorthStar banking schema and generators from `feature/postgresql-schema` without replacing the operational model.

This is a portfolio/research system. Alerts are review candidates, not findings of crime. Country ratings, EUR exchange rates and thresholds are synthetic demonstration inputs; they are not maintained regulatory or market data. The ML model learns the injected scenarios and has not been validated for real customers.

## What is implemented

| Stage | Runnable deliverable | External requirements |
|---|---|---|
| Banking data | Original customer/account/beneficiary generators plus a deterministic small demo | PostgreSQL |
| Transactions | Seeded baseline payments and structuring, velocity, high-risk corridor and rapid-movement scenarios | Existing active accounts or demo |
| Ingestion | Typed staging, SQL business checks, core FK/check validation, audit/quarantine and conflict-safe replay | PostgreSQL |
| Analytics | Four AML rules, customer features, daily activity and SQL quality audits | PostgreSQL |
| PySpark | Typed CSV → partitioned silver Parquet → daily gold Parquet; reconciled against SQL | Java 17, optional Spark dependencies |
| Risk ML | Customer-level train/holdout split, metrics, saved model, repeatable scoring | Local Python; synthetic labels |
| Snowflake | Explicit fact/feature/mart tables, environment authentication, transactional MERGE loader | Your account, role, warehouse, database/schema; live cloud acceptance still required |
| Dashboard | Looker Studio-compatible CSVs and step-by-step report setup | Your Google account and manual report creation |

No cloud deployment or live Snowflake load is claimed. See [verification](VERIFICATION.md) for actual checks and [runbook](RUNBOOK.md) for contracts and limitations.

For the interactive interface without a database, follow the [main README](../../README.md). This page covers the database and optional engines.

## Quick start

Run commands from the repository root with Python **3.12**, PostgreSQL **17 or 18**, and a fresh demo database. Docker is optional if you already run PostgreSQL.

```sh
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
# Edit .env: choose your own PGPASSWORD and correct connection settings.
docker compose up -d --wait
python -m aml init
python -m aml demo --customers 200 --per-account 30 --seed 42 --start 2026-01-01
python -m aml validate
python -m aml export
python -m aml train
```

For an existing server, create `northstar_bank` yourself and set `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, `PGPASSWORD` or `DATABASE_URL`. `init` creates schemas/tables but **does not create or drop a database**. It applies additive, checksum-tracked migrations and seeds only when all reference tables are empty. Do not manually rerun the original `sql/seed` scripts on populated data: their preserved `TRUNCATE ... CASCADE` statements can remove dependent records.

Outputs are ignored by Git:

- `data/generated/`: master CSVs, transactions, separate scenario labels.
- `data/gold/export/`: transaction facts, customer features, daily dashboard activity, alerts, risk scores, model and evaluation metrics.
- `data/spark/`: silver and gold Parquet snapshots (after optional Spark command).

Running the same demo against the same unchanged database replays identical records without duplicating them. Use a fresh demo database when changing seed, customer population, date range or transaction count. The demo includes all eligible active accounts, so use a dedicated database rather than mixing it into existing non-demo data.

## Existing data and original generators

The original schema, reference seeds, architecture documents and Python generation logic are retained. Account/beneficiary generators and the connection smoke script now use environment-based connections. Existing synthetic CSVs are no longer tracked; copies remain in the original branch history and can be regenerated.

```sh
python data-generator/generate_customers.py
python -m aml ingest customers data/customers.csv
python data-generator/generate_accounts.py
python -m aml ingest accounts data/accounts.csv
python data-generator/generate_beneficiaries.py
python -m aml ingest beneficiaries data/beneficiaries.csv
python -m aml generate --start 2026-09-01 --per-account 30
python -m aml ingest transactions data/generated/transactions.csv
python -m aml validate
python -m aml export
```

Choose a transaction start after account opening and at least 30 days before today. The original generators are intentionally preserved and may emit rows that fail the stricter loader (for example, future closed dates). Inspect rejected rows and correct/regenerate them; CLI ingestion exits with code 2 if any row is rejected. It does not silently mark partial loads successful. The original customer generator assumes the original seed IDs 1–20 and the account generator assumes the original 12 currencies; the new demo reads actual reference IDs.

## Optional engines

```sh
# Java 17 must be installed, with JAVA_HOME pointing to its home directory.
pip install -r requirements-spark.txt
python -m aml spark

pip install -r requirements-snowflake.txt
# Fill SNOWFLAKE_* in .env; interactive SSO is the default.
python -m aml warehouse
```

Spark consumes the validated `transaction_facts.csv` export and overwrites only its dedicated silver/gold snapshot directories. Snowflake uses natural-key MERGEs for safe replay; removed source rows are not deleted from the warehouse. Its SQL contracts do not contain personal names or IBANs. See [cloud configuration](SNOWFLAKE.md) before first load.

## Tests

```sh
# Unit/contract tests run without PostgreSQL; integration tests report explicit skips.
python -m pytest -q

# This role needs CREATEDB. Tests create and drop only random aml_test_* databases.
export AML_TEST_DSN='postgresql://YOUR_TEST_USER:YOUR_TEST_PASSWORD@localhost:5435/postgres'
python -m pytest -q

# Include real Spark execution and SQL/Parquet reconciliation.
AML_TEST_SPARK=1 SPARK_LOCAL_IP=127.0.0.1 python -m pytest -q
```

GitHub Actions runs the full suite against an isolated PostgreSQL service and Java 17. Snowflake tests exercise configuration, source contracts, parameterized staging, MERGE order and rollback using a fake connection; they do not establish live Snowflake correctness. No cloud credentials are needed for CI.

## Dashboard and project structure

Follow [dashboard setup](../../dashboard/README.md) to connect daily activity, alerts and customer risk scores to Looker Studio. Keep the three dataset grains separate to avoid inflated totals.

```text
aml/                  CLI, generation, ingestion, export, ML, Spark, Snowflake
sql/schema/           Preserved operational schema
sql/seed/             Preserved reference data (legacy destructive resets)
sql/migrations/       Additive pipeline audit tables and indexes
sql/analytics/        Views for facts, rules, features and daily activity
sql/tests/            Read-only quality checks
data-generator/       Original generators, environment-based database access
tests/                PostgreSQL integration, ML, Spark and Snowflake contracts
docs/operations/      Runbook, cloud configuration, verification and issue mapping
```
