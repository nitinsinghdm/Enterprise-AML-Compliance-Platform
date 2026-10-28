# NorthStar transaction network

Public browser demo: https://nitinsinghdm.github.io/aml-network/

The network is a static, read-only synthetic research interface. Its source is in
`web/network/`; the portfolio repository hosts an exact copy on GitHub Pages.
It needs no database, login, cloud credential or payment permission to explore.

## What the network means

- Solid points: bank accounts, labelled AC. Hollow circles: known external beneficiary records, labelled EX. Neither implies criminality.
- Diamonds: unidentified counterparties grouped by bank account and direction. They are **not** a shared account or inferred identity.
- Directed paths: payments aggregated by endpoints and status. Width represents value on a bounded logarithmic scale, not proportional risk.
- Small points on paths: individual recorded payments. Position along a path is for visual spacing, not time, geography or a risk score. Select a point or its ledger ID to inspect the record.
- Amber: repeated cash deposits; violet: payment bursts; cyan: rapid movement; rose: higher-risk corridors. White can indicate multiple patterns; select a flag to disambiguate. Colour is a pattern category, not severity.
- The timeline reveals cumulative records through the end of each UTC day. Daily alerts appear with their complete evidence. This does not simulate real-time detection latency or a streaming bank feed.

The default view contains completed payments. Select **All recorded payments** to
include pending and failed records. Non-completed paths are dashed and never
contribute to the existing rules. Metrics and downloads follow the current
account, status, pattern and day filters. Selecting a pattern shows supporting
payments only. Selecting an alert shows its supporting rows in the ledger;
selecting a transaction shows that one row. Reset restores the complete view.

## Evidence and source contracts

`aml.network.build_snapshot` uses a read-only repeatable-read PostgreSQL
transaction. It reads existing transaction facts and beneficiary IDs, and obtains
authoritative alert groups from `analytics.aml_alerts`. It reconstructs supporting
transaction sets for those groups and **refuses export** if the count or amount
differs from SQL. No database tables, seeds or detection thresholds are changed.

The velocity rule preserves SQL RANGE semantics, including simultaneous timestamps
and the inclusive one-hour boundary. Its alert amount counts triggering rows;
its evidence includes every row in their qualifying windows. Rapid movement
includes incoming contextual payments but counts each qualifying outgoing payment
once, even when it matches multiple incoming payments. Structuring and corridor
alerts include their qualifying rows. The interface distinguishes counted and
context rows. Alert amounts overlap and must not be summed as unique suspicious
volume. The synthetic ground-truth labels are not used to choose network alerts.

AC/CU/EX/TX identifiers are local snapshot aliases. The public JSON includes only
allowlisted fields and no customer names, banking credentials, IBANs, payment
references or original UUIDs. Aliases are not an anonymisation guarantee for real
financial records. **Never publish a real customer dataset.**

The checked-in `data.json` is a deliberate, small (~0.5 MB) synthetic fixture with
2,110 transactions and 30 alert groups, not a bulk CSV export. Every visible
connection has a source record. Incoming records without a source account and
outgoing records without a beneficiary remain unresolved; there are no fabricated
bank-account-to-bank-account links.

## Run and reproduce

Serve the interface locally:

```sh
python -m http.server 8766 --bind 127.0.0.1 --directory web/network
```

Open http://127.0.0.1:8766. Opening index.html via file:// will not load the JSON.

To rebuild from an isolated synthetic database, use the main setup guide and run
`python -m aml demo --customers 100 --per-account 20` in that isolated database.
Then, with DATABASE_URL pointing to it:

```sh
PYTHONPATH=. python scripts/build_network_preview.py --synthetic-data-confirmed
```

The confirmation is a required declaration, not an automatic proof that the source
is synthetic. Inspect provenance and use a disposable demo database.

Verification:

```sh
python -m pytest tests/test_network.py -q
pip install -r requirements-browser.txt
python -m playwright install chromium
# Start the local HTTP server above, then:
python scripts/check_network_browser.py
```

Database tests require AML_TEST_DSN and otherwise explicitly skip. Browser checks
exercise actual rendered controls, all four signal types, evidence roles, totals,
status filters, timeline, download, pagination, keyboard and mobile layout.

## Deployment and limits

Copy `web/network/` into the portfolio repository as `aml-network/`, commit and
merge through a pull request. GitHub Pages serves these public static files. The
README and project case study link directly to the public URL. No server secrets
are needed; Google Fonts, CDNs, trackers and external graph libraries are not used.
Inter is bundled under the accompanying SIL Open Font License.

This is not a bank-ready deployment: it has no identity provider, tenant isolation,
shared case persistence, operational review workflow, live transaction ingestion,
model validation on representative real data or authorised payment intervention.
The existing local Streamlit analytics interface remains available. Production
bank integration requires separate security, data, operational and compliance
work; synthetic demonstration results do not establish detection accuracy.
