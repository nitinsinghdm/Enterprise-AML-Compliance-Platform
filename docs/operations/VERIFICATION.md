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

## Interface update — 2026-10-27

- Full local suite: **38 passed** in 26.15 seconds, including all existing PostgreSQL/Spark checks and nine new dashboard tests.
- Streamlit interaction tests cover all four pages without a database, activity filters, empty selections, holdout filtering, bundled-preview totals, missing exports and checksum mismatch.
- Chromium browser verification exercised the running Overview, Alert explorer and Pipeline & guide pages. README PNGs are actual captures of the bundled synthetic preview.
- The exporter now includes four recorded ingestion batches and eight SQL audit results in the saved demo snapshot. The approximately 65 KB preview contains summary rows only.
- No cloud deployment, live bank feed, background job scheduler or hosted dashboard is claimed. The local interface reads bundled data or the latest exported files.

### Portfolio visual finish — 27 October 2026

Updated the dashboard palette and README screenshots to match the author's portfolio. The complete PostgreSQL 18 / Java 17 suite passed again: **38 passed in 29.06s**. Chromium captured the rendered Overview and Alert explorer and checked the guide page. No live Snowflake or Looker Studio validation was performed. The portfolio case study links to the runnable local interface and its setup instructions.

### Guided dashboard and typography — 27 October 2026

The interface now introduces the AML purpose, uses plain-language patterns and review prompts, and keeps technical records in expandable sections. Nine dashboard interaction tests pass. Chromium verified the bundled Inter font loaded at heading weight 650, no phone-width horizontal overflow, and the rendered overview, alert explanation and guide pages. Data calculations and detection rules are unchanged.

### Public transaction network — 28 October 2026

- Complete local suite: **43 passed in 15.91s**, including PostgreSQL, Spark, the existing Streamlit interface and new network evidence tests.
- Reconciled all 30 SQL alert groups against their counted and contextual payment records. The committed 2,110-payment public fixture equals a freshly generated test database snapshot.
- Tested inclusive one-hour velocity boundaries, simultaneous timestamps, exclusion of failed payments, and rapid-movement support without double counting.
- Chromium acceptance covers totals, all four patterns, individual transaction inspection, status/account filtering, daily replay, CSV export, pagination, keyboard controls, and a 390px mobile viewport.
- The browser workflow is included in GitHub Actions. Local and CI tests do not establish real-world detection accuracy or production bank readiness.
- No real banking credentials, customer data or live bank connection used. Snowflake and Looker Studio cloud acceptance remains unchanged.

### Expanded event-time replay — 28 October 2026

- Complete local PostgreSQL 18 / Java 17 / Spark suite: **45 passed in 101.99s**.
- Reproducible isolated fixture: **250 accounts, 10,281 transactions, 74 final alert groups and 127 evidence versions**. Public JSON is approximately 2.38 MB; no bulk CSVs or secrets are committed.
- New tests prove no alert version references future payments and reconcile representative event-time SQL prefixes to exported counts and amounts. Final versions match the authoritative SQL groups.
- Chromium acceptance passed for all four exact first-trigger boundaries, guided replay, next payment, UTC jump, normal body casing/uppercase headings, filters, CSV export, evidence, keyboard controls and 390px mobile layout. README captures show the actual rendered interface.
- Simulated event time is not processing latency. No real bank connection, representative-data validation or production readiness claim is made.

### Analyst review workspace — 28 October 2026

- Chromium checks passed for account details, radio status changes, browser-local persistence across reloads, review filtering, safe text rendering, JSON export and storage-denied fallback.
- Guided replay retains history and pauses at the first burst trigger. Tests verify this at accelerated speed, and rolling-window explanations distinguish expired view records from deleted payments.
- Silent Web Audio instrumentation verifies a 440 Hz new-alert tone and two 880 Hz tones when a burst reaches 12 payments. Sound is opt-in; higher priority is a documented demo policy, not model validation.
- Existing network browser acceptance also passed, including first-trigger timing and mobile layout. Review browser acceptance is included in CI. No detection SQL, database schemas or financial data changed.
- Restored the portfolio blueprint cover and replaced the outdated workflow diagram. README now explains the investigation story and links to code/setup guides.

### Focused map, labels and playback rates — 29 October 2026

- Browser acceptance verifies 0.1×, 0.5×, 1.0×, 1.5× and 2× against a controlled clock, pause behavior and changing rates during playback without duplicate timers or cursor reset.
- Full-width map defaults to flagged connections; tests verify the all-payments switch preserves metrics, the four pattern cards, and Start an AML Review opening evidence for an account.
- Targeted UI labels use Title Case, the crime disclaimer is uppercase, and explanatory body copy stays sentence case. Existing alert-evidence and local review browser checks pass. Detection SQL, synthetic data and account annotations are unchanged.

### Currency filters and account follow-up — 29 October 2026

- Full local suite: **45 passed in 61.27s**, no skips, with PostgreSQL 18 and Java 17 / Spark enabled in an isolated test database.
- All three Chromium acceptance scripts passed: network, review and new filter/workflow coverage. Checks include combined filters, complete alert evidence, return navigation, source context, escalation rationale, audio gain/mute and mobile layout.
- Fresh fixture matches the committed export, source currency matches account currency, and fixed demonstration FX reconciles to EUR. All previous EUR amounts, 74 final alert groups and alert event versions were preserved.
- Portfolio grey palette and snake verified in dark/light themes and at mobile width. Striped N monogram replaces the header wordmark across all six pages and the favicon.
- Review status and history remain browser-local; no bank feed or external case assignment was added.
