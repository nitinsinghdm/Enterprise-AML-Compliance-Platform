# Looker Studio dashboard setup

For the local interactive interface, see the [main README](../README.md) and [interface guide](../docs/operations/INTERFACE.md). This document covers the optional Google report.

The deliverable is a compatible dataset and reproducible setup, not a published Google report. No Google credentials are needed to produce CSVs. Use synthetic data only for this demo.

1. Run `python -m aml export` followed by `python -m aml train`.
2. In Looker Studio, create a blank report and add a **File Upload / CSV** data source for each file below. Alternatively, import each CSV into a separate Google Sheet and connect the sheets. Replace the sheet contents on refresh rather than appending the same snapshot.
3. Confirm field types below. UUIDs and model versions must be **Text**, numeric metrics **Number**, dates **Date** (YYYY-MM-DD). CSV decimals use `.`.
4. Add three pages. Each page uses its own data source. Do not join raw daily/alert/customer rows: their grains differ.

## Activity page: `dashboard_daily.csv`

Grain: UTC date × destination country × channel. Fields:

| Field | Type / aggregation |
|---|---|
| transaction_date | Date; default date range dimension |
| destination_country | Text, ISO-2; optionally Geo → Country |
| channel | Text |
| transaction_count | Number, SUM (all statuses) |
| completed_count | Number, SUM |
| completed_amount_eur | Currency EUR, SUM |
| cross_border_count | Number, SUM (completed only) |

Add date, country and channel filters; scorecards for transaction count, completed count and EUR volume; a daily volume time series; country and channel bar charts. Calculated completion rate: `SUM(completed_count) / SUM(transaction_count)`. Average completed payment: `SUM(completed_amount_eur) / SUM(completed_count)`; show null when the denominator is zero. Monetary totals use fixed synthetic conversion rates, not live FX.

## Monitoring page: `alerts.csv`

Grain: customer × account × date × rule. Use Record Count for **alert groups**, not suspicious transactions or unique customers. Add rule/date filters; counts by rule; a review table with customer_id, account_id, date, rule, evidence_count and amount_eur. A transaction may contribute to multiple rules. **Do not sum alert amount_eur across rules and call it unique suspicious volume.** Velocity evidence counts are the largest trailing-hour count, while its amount is the sum of triggering rows only.

## Customer risk page: `customer_risk_scores.csv`

Grain: one row per labeled customer for this model run. Set customer_id and model_version to Text. Add risk-band counts, score distribution and a ranked customer table. Display evaluation_split (train/holdout); holdout metrics in `metrics.json` are the only evaluation metrics. Scores are 0–100 synthetic scenario likelihood rankings, not calibrated money-laundering probabilities.

## Refresh and acceptance

Regenerate exports from a consistent PostgreSQL snapshot, retrain when the feature population changes, and replace all dashboard data sources together. File-upload connectors can append rows; remove the prior upload before adding the replacement. Verify total transactions and completed EUR volume against:

```sql
SELECT sum(transaction_count), sum(completed_amount_eur)
FROM analytics.dashboard_daily;
SELECT rule_code,count(*) FROM analytics.aml_alerts GROUP BY rule_code;
```

Show a visible subtitle: **Synthetic AML demonstration — not production compliance monitoring**. Never upload actual customer names, account numbers or confidential records to this public portfolio workflow. No customer PII is exported, but pseudonymous IDs would still need access controls with real data.

Connector reference: [Google CSV upload documentation](https://docs.cloud.google.com/data-studio/upload-csv-files).
