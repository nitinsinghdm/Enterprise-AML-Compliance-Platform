# Delivery and issue mapping

Implementation is on `codex/complete-aml-platform`, based on `feature/postgresql-schema`. The pull request targets main and includes the earlier schema/design work that was absent from main. Existing feature branches remain intact. Issue checklists distinguish code implementation from merge, deployment and account acceptance.

| Issue | Delivered | Remaining |
|---|---|---|
| #11 PostgreSQL database | Preserved schema, constraints and seeds; additive indexes and audited ingestion | Review/merge branch; use your intended database |
| #12 Synthetic banking data | Existing master generators, deterministic demo, transactions and four labeled scenarios | Review/merge |
| #13 SQL analytics | Four rules, features, fact/daily views and quality audit | Review/merge |
| #14 PySpark ETL | Typed silver/gold Parquet, reconciliation and replay tests | Review/merge; install Java 17 on deployment host |
| #15 Snowflake warehouse | Environment auth, typed tables, staged transactional MERGE and contract tests | Provision account objects, run live load/replay/permission acceptance |
| #16 Risk model | Customer-disjoint evaluation, metrics, persistence and inference | Review/merge; real-data validation is out of scope |
| #17 Executive dashboard | Compatible CSV datasets, three-page Looker Studio setup and reconciliation instructions | Create/connect/publish report in user's Google account |

Do not close cloud or publication work solely because a local mock test passed. The earlier business-analysis issues are not altered by this implementation.
