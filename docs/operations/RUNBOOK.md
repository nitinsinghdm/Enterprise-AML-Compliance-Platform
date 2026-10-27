# Pipeline runbook and contracts

## Flow

Original or demo master data → audited staging → PostgreSQL core → synthetic transactions → audited staging/core → SQL facts/rules/features → consistent CSV snapshot → (a) local ML, (b) Spark Parquet, (c) Snowflake marts, (d) Looker Studio.

`python -m aml --help` lists all commands. Run from the repository root. `.env` is loaded without overriding existing environment variables. No secrets or connection strings are logged intentionally. Keep private keys outside the repository. The default Docker database listens only on localhost.

## Ingestion and recovery

The loader accepts only allowlisted entities and table columns. CSV headers must be unique and include required columns. Incoming values are cast by PostgreSQL into a temporary table shaped like the existing core table. SQL checks enforce date/balance, active ownership, currency, timestamp and beneficiary rules; core constraints enforce PK/FK, required fields and enumerations. Each record uses a savepoint. Data errors are quarantined while valid rows commit in the same audited batch. Unexpected infrastructure or programming errors roll back the batch.

`staging.ingestion_batches` stores file SHA-256, entity, row counts and completion time; `staging.ingestion_rows` stores row number, raw JSON, status and an error category. The shared staging table supports all four entities; original customers_raw/accounts_raw tables remain unchanged for compatibility. An exact typed-value duplicate is REPLAYED; the same natural key with changed values is REJECTED, not silently overwritten. Corrections need a deliberately reviewed update to core data or a new legitimate key. The loader is append-only, not a CDC/upsert service.

```sql
SELECT batch_id,entity,accepted,rejected,replayed,finished_at
FROM staging.ingestion_batches ORDER BY started_at DESC;
SELECT row_number,reason,payload FROM staging.ingestion_rows
WHERE batch_id = 'YOUR_BATCH_UUID' AND status='REJECTED' ORDER BY row_number;
```

Payloads can contain PII when loading real records; restrict staging access and define retention before such use. Row-at-a-time savepoints favor transparent validation for portfolio-sized datasets, not high-throughput production ingestion. Spark starts from the validated snapshot and provides the distributed transformation example.

## Transaction generation

`demo` creates deterministic UUIDs, 1 account and 1 beneficiary per customer. The original scripts still support their original 10K/12K/18K workflow. `generate` queries active customers/accounts opened on/before the start date and actual reference IDs. Baseline activity uses skewed payment amounts, varied daytime timestamps, channels, payment types and realistic completed/failed/pending proportions. Active customer-owned beneficiaries are used for transfers where available; a null beneficiary means an external/unregistered counterparty. Beneficiary country and account currency are validated.

Twenty percent of customers receive one of four injected patterns, distributed across customers: repeated near-threshold incoming cash; bursts within an hour; large cross-border payments to the preserved HIGH-rated reference countries; incoming/outgoing movement within 20 minutes. `scenario_labels.csv` is separate from operational transaction input and never becomes an ML predictor. Baseline does not prove legitimate behavior; it simply means no intentionally injected scenario.

All timestamps use naive **UTC** to preserve the original TIMESTAMP schema. All comparisons and exports assume UTC; configure your database session timezone as UTC if migrating to timestamp-with-time-zone. A 30-day window must be wholly in the past. FX is **EUR per source-currency unit** and `amount_eur = round(amount * exchange_rate, 2)`. The generator is not a double-entry ledger: it does not post balance changes, reserve funds or ensure funding sufficiency. Existing account balances remain snapshots.

Stable replay requires the same seed, start date, eligible account population, reference IDs and per-account count. Use distinct databases for different experiments. Do not mix synthetic fixtures into real customer databases.

## SQL analytics

Only COMPLETED payments contribute to alerts or model aggregates. Four educational rules are implemented in `sql/analytics/01_monitoring.sql`:

| Rule | Definition |
|---|---|
| STRUCTURING | >=3 incoming CASH_DEPOSIT payments of EUR 8,000–<10,000, totaling >=24,000 per account/day |
| VELOCITY | >=10 completed transactions in a trailing hour per account (not clock-hour buckets) |
| HIGH_RISK_CORRIDOR | Cross-border completed amount >=EUR 10,000 to a HIGH/CRITICAL reference country |
| RAPID_MOVEMENT | Outgoing >=EUR 9,000 within one hour after incoming, outgoing 80–120% of incoming |

Alerts are account/day/rule groups and can overlap. Repeated execution reads the current core data rather than persisting duplicate alerts. There is no sanctions list integration, name matching, case-management workflow or automated regulatory reporting. Country risk ratings are inherited project fixtures, not current sanctions advice.

`python -m aml validate` runs SQL audits and exits nonzero for violations. It does not repair records. Database constraints already prevent many structural failures; audits catch data that bypassed the loader.

## Export and ML

Export uses a read-only REPEATABLE READ database transaction. The manifest records row counts, checksums and UTC export time. Keep the exported CSVs together as a snapshot, including pipeline_batches.csv and quality_checks.csv. The exporter streams rows, while generation/modeling and the warehouse CSV loader are intended for data that fits local memory.

ML uses numeric customer behavior features and PEP indicator, with an explicit feature allowlist excluding IDs, scenario labels and alerts. The target is whether the customer has any injected scenario. One feature row per customer and a stratified customer split prevent the same customer appearing in both training and holdout. No temporal generalization test is claimed. The model is not refit on the holdout before reporting metrics. Scores for training customers are marked `train`; holdout scores are marked `holdout`.

The demo may yield very high metrics because patterns are deliberately separable. Real deployment would require representative independently labeled data, temporal validation, calibration, threshold/false-positive cost analysis, fairness/drift evaluation and human review. PEP flags alone are not a finding. `predict` accepts only a trusted locally produced joblib model; loading untrusted pickle/joblib can execute code.

Example inference:

```sh
python -m aml predict --features data/gold/export/customer_features.csv \
  --model data/gold/export/risk_model.joblib --output data/gold/export/predictions.csv
```

## Spark and operations

Install Java 17 and requirements-spark.txt. Spark explicitly types the CSV contract, rejects malformed/null key/invalid amount and duplicate IDs, writes date-partitioned silver Parquet, and creates gold daily aggregates matching SQL. It assumes the source is the validated PostgreSQL export; it does not independently repeat every PostgreSQL FK check. It overwrites its dedicated snapshot directories and is not an atomic multi-directory publication service. Use a new output directory per production-like run and promote only after validation; concurrent writes to the same directory are unsupported.

Apply schema changes as new numbered migrations. Bootstrap checks the content hash of applied files. Existing schema/seed files are preserved. Partial reference seeding fails safely rather than cascading truncations. SQL analytics views are replaceable on `init`; add separate migration steps if changing their output column contracts.

For shutdown, `docker compose stop` preserves the database volume. Removing that volume is destructive and is not part of setup or tests. Tests use randomly named disposable databases only, never reset your chosen PGDATABASE.
