# Verification record

Verified locally on **2026-10-24** with Python 3.12, PostgreSQL 18, Java 17 and PySpark 3.5.3. A dedicated temporary PostgreSQL server was used; tests created/dropped random `aml_test_*` databases. No existing user database was reset.

## Results

- Full suite: **29 passed**, no skips, including real Spark execution (13.77 seconds).
- Separate CLI demo: 100 customers, 100 accounts, 100 beneficiaries and **2,110 transactions** ingested; zero rejects.
- Generator: 2,000 baseline transactions and **110 deliberately suspicious scenario transactions**.
- Export: 2,110 fact rows, 100 customer feature rows, 66 daily aggregate rows and 30 account/day/rule alert groups.
- CLI SQL audit: **8 checks, zero violations**.
- Customer model: 75 training customers and 25 holdout customers. Synthetic holdout ROC AUC and average precision both 1.0. This reflects easy injected patterns and is **not real-world model validation**.
- Spark: typed silver/gold Parquet produced; every gold aggregate matched the PostgreSQL CSV; rerun was stable; duplicate transaction input rejected.
- Dependency consistency (`pip check`), Python compilation and Git whitespace checks passed.

The test suite covers safe bootstrap replay, generator determinism, exact record replay, conflicting duplicates, malformed money, NaN, invalid FX, foreign keys, enums, timestamps, currency mismatch, frozen accounts, all four AML scenarios, exclusion of failed payments, export reconciliation, customer holdout scoring, model persistence/inference, Snowflake config validation, staged-load transaction order and rollback.

## Boundaries

- Snowflake dependency installed and configuration/loader contracts tested with a fake connection. **No live Snowflake authentication, provisioning, load or warehouse permission test was run.** Follow SNOWFLAKE.md and keep issue #15 open until cloud acceptance.
- Looker Studio-compatible datasets and report instructions are complete. **No Google report was created or published.** Follow dashboard/README.md; keep the publication checkbox open in issue #17.
- Docker Compose is provided; this machine had no Docker executable, so database tests used a separate native PostgreSQL instance. CI specifies PostgreSQL 17 and Java 17; its remote result must be checked on the pull request.
- No production sanctions screening, case management, regulatory filing or real-customer validation is included.
- Original schema, seed files and generator logic were retained. Only legacy database connection configuration changed. Existing CSV snapshots and OS metadata were removed from the new branch's tracked tree; original history remains available.
