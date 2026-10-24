# Snowflake deployment and acceptance

The loader and local contract tests are implemented. A real connection, role permissions and SQL execution in your Snowflake account have **not** been verified. This is the remaining cloud acceptance step.

## Provisioning (account administrator)

Create or choose a dedicated demo warehouse, database, schema and least-privilege loader role. The loader deliberately does not provision them or change grants. A representative setup is below; adapt names, sizes, ownership and user assignment to your account policy. Creating/running a warehouse can incur cloud charges.

```sql
CREATE WAREHOUSE IF NOT EXISTS AML_DEMO_WH
  WAREHOUSE_SIZE='XSMALL' AUTO_SUSPEND=60 AUTO_RESUME=TRUE INITIALLY_SUSPENDED=TRUE;
CREATE DATABASE IF NOT EXISTS AML_DEMO;
CREATE SCHEMA IF NOT EXISTS AML_DEMO.ANALYTICS;
CREATE ROLE IF NOT EXISTS AML_DEMO_LOADER;
GRANT USAGE ON WAREHOUSE AML_DEMO_WH TO ROLE AML_DEMO_LOADER;
GRANT USAGE ON DATABASE AML_DEMO TO ROLE AML_DEMO_LOADER;
GRANT USAGE, CREATE TABLE ON SCHEMA AML_DEMO.ANALYTICS TO ROLE AML_DEMO_LOADER;
-- Assign AML_DEMO_LOADER to the intended user under your account policy.
```

If target tables already exist under another owner, grant SELECT, INSERT and UPDATE on those tables to the loader role. The loader owns tables it creates. Use a separate read-only role for a dashboard and grant only USAGE and SELECT. Never grant ACCOUNTADMIN to the application.

## Configuration

Copy `.env.example` to untracked `.env`. Set account identifier, user, warehouse, database, schema and role. Warehouse/database/schema/role must be simple identifiers (letters, digits, underscore, dollar sign); quoted mixed-case object names are not supported by this demo.

- Interactive use: `SNOWFLAKE_AUTHENTICATOR=externalbrowser` uses your browser SSO/MFA.
- Scheduled jobs: `SNOWFLAKE_AUTHENTICATOR=SNOWFLAKE_JWT`, `SNOWFLAKE_PRIVATE_KEY_FILE` pointing outside the repo, and optional `SNOWFLAKE_PRIVATE_KEY_FILE_PWD`. Register the public key with the user through your administrator.
- Password mode: `SNOWFLAKE_AUTHENTICATOR=snowflake` and `SNOWFLAKE_PASSWORD`; account MFA/security policies may prohibit unattended password login.

The connector keeps TLS verification enabled and has bounded login/network timeouts. Do not put credentials in command-line arguments, source control, notebooks or screenshots.

```sh
pip install -r requirements-snowflake.txt
python -m aml export
python -m aml train
python -m aml warehouse
```

## Warehouse contract

| CSV | Table | Key / grain |
|---|---|---|
| transaction_facts | FACT_TRANSACTIONS | transaction_id |
| customer_features | DIM_CUSTOMER_RISK_FEATURES | customer_id, current aggregate features |
| dashboard_daily | MART_DAILY_ACTIVITY | date/country/channel |
| alerts | FACT_AML_ALERTS | customer/account/date/rule |
| customer_risk_scores (optional) | MART_CUSTOMER_RISK | customer_id/model_version |

The exact SQL types live in `aml/warehouse.py`. Transaction facts retain source amount, source currency and normalized EUR amount. Customer feature tables do not expose names, IBANs, birth dates or addresses. Pseudonymous IDs still require appropriate access controls if adapted to real data.

All CSV headers and natural-key uniqueness are checked. Values use connector parameters; SQL identifiers come from fixed contracts. Each CSV is staged in a session-temporary table in batches of 1,000. All CREATE statements happen **before** BEGIN because Snowflake DDL commits implicitly. Target MERGEs then share one explicit transaction and roll back together on failure. A failed first load may leave empty permanent target tables; retrying is safe.

This is a small explicit SQL mart loader, not a bulk COPY/Snowpipe implementation or an SCD2 warehouse. It reads each CSV into memory and upserts snapshots. Replays do not add rows with the same natural key. **Absence from a later snapshot does not delete a prior warehouse row** (including resolved alerts). Use a fresh demo schema for each independent experiment. Concurrent loaders and source deletions need a production orchestration/reconciliation policy.

## Live acceptance checklist

1. Run the export/model commands on a known synthetic fixture.
2. Authenticate and run `python -m aml warehouse`; compare returned row counts to the manifest (plus risk-score CSV count).
3. Run the same load again and confirm stable row counts and totals.
4. Check source and warehouse counts, completed EUR totals and grouped alert counts.
5. Verify the dashboard role can SELECT but cannot INSERT/UPDATE.
6. Keep this cloud step open in issue #15 until these checks pass in your account.

```sql
SELECT COUNT(*) FROM FACT_TRANSACTIONS;
SELECT SUM(AMOUNT_EUR) FROM FACT_TRANSACTIONS WHERE TRANSACTION_STATUS='COMPLETED';
SELECT SUM(COMPLETED_AMOUNT_EUR) FROM MART_DAILY_ACTIVITY;
SELECT RULE_CODE,COUNT(*) FROM FACT_AML_ALERTS GROUP BY RULE_CODE;
SELECT TRANSACTION_ID,COUNT(*) FROM FACT_TRANSACTIONS GROUP BY TRANSACTION_ID HAVING COUNT(*)>1;
```

Sources: [Snowflake Python Connector API](https://docs.snowflake.com/en/developer-guide/python-connector/python-connector-api), [Snowflake transactions](https://docs.snowflake.com/en/sql-reference/transactions), [MERGE](https://docs.snowflake.com/en/sql-reference/sql/merge).
