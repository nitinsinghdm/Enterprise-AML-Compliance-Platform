# ENTERPRISE AML COMPLIANCE PLATFORM

**Trace the payment. Explain the alert.**

NorthStar is a synthetic banking project that shows how transaction records become explainable anti-money laundering (AML) alerts. Follow payments between recorded accounts and beneficiaries, watch a suspicious pattern develop, and inspect the evidence behind each flag.

**[Open the transaction network →](https://nitinsinghdm.github.io/aml-network/)** · [Portfolio case study](https://nitinsinghdm.github.io/aml.html) · [Full setup](docs/operations/SETUP.md)

![NorthStar transaction network with timestamped replay and AML alerts](images/network-overview.png)

## TRY IT IN THREE STEPS

1. Select **Watch an alert form**. The view focuses on one synthetic account and replays its payments.
2. Watch the UTC clock. A payment burst raises an alert when the rule's threshold is reached.
3. Select the alert. Read why it appeared and inspect the exact payments counted by the rule.

Use **Next payment** to skip quiet periods, jump to an exact UTC second, or replay one second, minute or hour per tick. Filter the last hour or 24 hours to examine a smaller slice of activity.

This is **simulated event-time replay**, not a live bank connection. Alerts use only evidence available at the displayed time. A flag means “review this pattern,” not “this is a crime.”

## WHAT THE NETWORK SHOWS

| On screen | Meaning |
|---|---|
| Solid account points | Synthetic bank accounts |
| Hollow points | Recorded external beneficiaries |
| Diamonds | Unidentified counterparties; no shared identity is assumed |
| Lines and payment points | Recorded payment connections and individual transactions |
| Coloured signals | The type of AML pattern, not a verdict or severity rating |
| Evidence ledger | Payments behind the selected alert, with counted and contextual rows separated |

The public fixture contains **10,281 transactions across 250 accounts**, with **74 account/day/rule alert groups** over the complete period. Completed payments are shown by default; failed and pending records remain inspectable. Counts change with your filters and replay time.

![Selected AML alert and its supporting payment evidence](images/network-evidence.png)

## FOUR PATTERNS TO INVESTIGATE

| Pattern | What triggers a review |
|---|---|
| Repeated cash deposits | Several near-threshold deposits accumulate on one account |
| Payment burst | At least 10 completed payments within a trailing hour |
| Rapid money movement | Funds leave soon after a similarly sized incoming payment |
| Higher-risk corridor | A large cross-border payment involves a higher-rated fixture country |

Exact rules appear in the interface and in [SQL](sql/analytics/01_monitoring.sql). Thresholds and country ratings are demonstration assumptions. Alert amounts can overlap across rules and must not be summed as unique suspicious volume.

## HOW IT WORKS

![Synthetic banking pipeline architecture](images/pipeline.svg)

**Generate → Validate → Monitor → Explain**

Python produces repeatable synthetic activity. PostgreSQL validates and ingests accepted records, tracks rejected rows and prevents duplicate loads. SQL identifies monitoring patterns. The browser links those patterns to payment evidence; the local analytics dashboard explores summaries and customer risk scores.

The original banking schemas, reference data and master-data generators are preserved.

| Component | What is available |
|---|---|
| PostgreSQL and Python | Reproducible generation, staging-to-core ingestion, quality checks and audited exports |
| Public browser interface | Transaction graph, second-resolution replay, point-in-time alerts, evidence and CSV export |
| Streamlit analytics | Local payment overview, alert exploration, customer scores and pipeline status |
| Risk-scoring ML | Synthetic customer classification with a separate holdout evaluation; real-world accuracy is unvalidated |
| PySpark | Typed silver/gold Parquet processing and reconciliation tests |
| Snowflake | Environment-configured warehouse loader; your account and live acceptance checks are required |
| Looker Studio | Compatible datasets and a setup guide; report publishing requires your account |
| GitHub Actions | Database, Spark, interface and browser checks; required integration check protects main |

## RUN IT LOCALLY

The browser interface needs only Python to serve its bundled synthetic data:

```sh
python -m http.server 8766 --bind 127.0.0.1 --directory web/network
```

Open **http://127.0.0.1:8766**. No database, login or cloud credentials are needed for this preview.

For the local analytics dashboard, use Python 3.12:

```sh
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dashboard.txt
streamlit run dashboard_app.py
```

Open **http://localhost:8501**. On Windows, activate with `.venv\Scripts\activate`. Its bundled summary/model preview is a separate, smaller 100-customer dataset, not the expanded browser fixture.

To run the full pipeline, follow the [database and dependency setup](docs/operations/SETUP.md), then:

```sh
python -m aml demo --customers 250 --per-account 40
python -m aml validate
python -m aml export
python -m aml train
```

[Network fixture reproduction](docs/operations/NETWORK.md) uses an isolated temporary database and adds deterministic seconds to timestamps for replay. Generated bulk CSVs and secrets stay out of Git.

## POTENTIAL VALUE FOR A BANK

The product hypothesis is **less time spent reconstructing why an alert appeared**. Each flag connects a versioned rule, its trigger time, the account and the exact payment evidence. Unknown counterparties remain explicit, and reviewers can distinguish counted payments from supporting context.

This is a proposed value proposition, not a proven market advantage. A bank pilot would need to measure analyst review time, false-positive workload and detection quality on representative data. Synthetic results cannot establish production readiness.

The current demo does not provide live bank ingestion, production access controls, tenant isolation or shared case management. It does not block payments. Broader cybersecurity and the separate SentinelPay product are future work.

## VERIFY AND EXPLORE

```sh
pip install -r requirements-dev.txt -r requirements-dashboard.txt
python -m pytest -q
```

Database and Spark tests require the configuration in the [testing guide](docs/operations/SETUP.md#tests); unavailable integration dependencies are explicitly skipped. Browser checks cover filters, exact alert trigger times, evidence, export, replay and mobile layout.

- [Network meaning, replay contracts and browser checks](docs/operations/NETWORK.md)
- [Verification record](docs/operations/VERIFICATION.md)
- [Pipeline operations and recovery](docs/operations/RUNBOOK.md)
- [Snowflake configuration](docs/operations/SNOWFLAKE.md)
- [Looker Studio setup](dashboard/README.md)
- [Original database design](docs/database/Database-Design.md)

```text
aml/                 Pipeline, model, Spark, warehouse and network export
sql/                 Banking schema, validation and monitoring rules
web/network/         Public browser interface and synthetic fixture
dashboard_app.py     Local Streamlit analytics interface
tests/               Data integrity, reconciliation and interface tests
docs/operations/     Setup, operational contracts and verification
```

**Nitin Singh** · Data Analytics & Data Engineering · [Portfolio](https://nitinsinghdm.github.io/)
