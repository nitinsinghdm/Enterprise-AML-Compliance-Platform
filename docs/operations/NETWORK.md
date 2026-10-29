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
- The UTC timeline reveals records at one-second resolution. Each alert appears only when its rule qualifies, and its evidence grows as later payments arrive. Replay Step selects one second, minute or hour of simulated event time per tick. Playback Speed offers 0.1×, 0.5×, 1.0×, 1.5× and 2×. At 1.0× a tick takes one wall-clock second; at 0.1× it takes ten seconds and at 2× it takes half a second. Changing speed during playback replaces the timer without resetting the cursor. This is not a live bank feed or a detection latency benchmark.

The default view contains completed payments. Select **All recorded payments** to
include pending and failed records. Non-completed paths are dashed and never
contribute to the existing rules. Metrics and downloads follow the current
account, status, pattern and time filters. The last-hour/24-hour filters show payments and alert versions updated in that window. Selecting a flag also includes earlier supporting context, so evidence is not silently truncated. Selecting a pattern shows supporting
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

The checked-in `data.json` is a deliberate synthetic browser fixture with
10,281 transactions, 250 accounts and 74 final alert groups, not a bulk CSV export. Every visible
connection has a source record. Incoming records without a source account and
outgoing records without a beneficiary remain unresolved; there are no fabricated
bank-account-to-bank-account links.

## Run and reproduce

Serve the interface locally:

```sh
python -m http.server 8766 --bind 127.0.0.1 --directory web/network
```

Open http://127.0.0.1:8766. Opening index.html via file:// will not load the JSON.

To rebuild, point DATABASE_URL at a local PostgreSQL admin database with CREATEDB
permission, then run:

```sh
PYTHONPATH=. python scripts/build_network_preview.py --synthetic-data-confirmed
```

The builder creates a disposable database, uses the original generator with 250
customers and 40 baseline payments per account, adds deterministic seconds to the
fixture timestamps, exports, and drops that temporary database. Existing data in
the configured database is not changed. The fixture helper rejects nonempty
customer tables. The original generator's behavior remains unchanged.

Snapshot version 2 includes final SQL alert groups and timestamped alert versions.
Every version uses only payments at or before its timestamp; simultaneous payments
are evaluated together. Final amounts/counts reconcile to SQL, and tests compare
SQL views filtered at representative prefix times with the exported versions.
First-trigger time remains separate from the latest evidence-update time. Alerts
are account/day/rule groups, not one alert per payment. No ground-truth scenario
label is used to trigger an alert.

**Watch an alert form** starts just before the first payment in a qualifying burst,
focuses the account with all arrived history visible and advances one minute per tick. It pauses at the first qualifying burst so the evidence can be inspected. **Next payment** advances
to the next recorded payment for the selected account, irrespective of status or
pattern filters. UTC jump supports an exact second. Playback pauses when the tab
is hidden. Refreshing resets the replay view. Optional review statuses and notes persist in browser localStorage for this dataset only; storage failures are disclosed and notes can be exported.

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
Inter and IBM Plex Mono are bundled with their accompanying SIL Open Font Licenses. Body copy uses normal sentence case; headings remain uppercase.

This is not a bank-ready deployment: it has no identity provider, tenant isolation,
shared case persistence, operational review workflow, live transaction ingestion,
model validation on representative real data or authorised payment intervention.
The existing local Streamlit analytics interface remains available. Production
bank integration requires separate security, data, operational and compliance
work; synthetic demonstration results do not establish detection accuracy.

## Browser-local review workspace

Transaction network, Account reviews and How to investigate are separate navigation views. Account details show all arrived account records regardless of graph filters, explicitly distinguish flows from balances, and expose only the fields present in the public fixture. Known beneficiary nodes show connected record counts; unknown endpoints never gain an invented identity.

Radio buttons record Not marked, Watch, Under review, Escalated for review or Review closed. Marked accounts gain a square outline. Notes are limited to 1,000 characters and rendered as text. Storage is scoped to the synthetic dataset fingerprint, is not synchronised or authenticated, and provides no compliance audit trail. Export produces a JSON copy. Never enter real personal information.

Sound defaults off and requires a user click. Forward replay produces one soft tone when an alert first triggers, or two higher tones when a burst first reaches 12 completed payments within an hour or a second distinct rule first flags the same account. At most one sound sequence plays per tick. Seeking/filtering/initial load are silent, and visual announcements remain available. This is a transparent demo review-priority policy, not a calibrated risk model.

## Focused map and review entry points

The map occupies a full-width section; filters sit above it and the alert queue/evidence inspector below. Flagged Connections draws only payment records that support currently visible alerts (plus an explicitly selected payment). All Payments draws all matching records. Metrics and ledger totals do not change when this map-only control changes, and the on-screen explanation discloses that distinction.

Pattern cards follow replay time, account, status and time window while comparing all four rules independently of the selected pattern. Clicking a card or Start an AML Review selects an available alert, preferring the documented demo higher-priority policy and then latest evidence update. The selected alert opens all arrived history so contextual evidence stays visible. No new statistical detection claim or finding of crime is made.


## Currency, filters and review workflow

The public fixture contains 3,288 EUR, 3,691 USD and 3,302 GBP transactions. Each account uses one source currency. Fixed **synthetic demonstration rates** (EUR 1, USD 0.8, GBP 0.9 EUR per unit) preserve every existing EUR transaction amount and SQL alert result; these are not market or live FX rates. Original amounts and currency appear in payment details, the ledger and CSV. Aggregate values and AML thresholds remain EUR.

Country, currency, transaction type, channel and direction filters combine. An alert qualifies when at least one supporting payment matches; opening it clears these filters to display its complete evidence. Back to All Payments clears account, pattern and detail filters, selects all statuses and history, and preserves the replay cursor.

Account details expose recorded counterparties and unidentified incoming/outgoing groups, with counts, EUR value, available countries, currencies, channels and first/latest times. Missing source identifiers remain unknown; a country field does not establish a person's location or a shared owner.

Map Symbols explains endpoint shapes, payment points/direction, pending/failed paths and W/R/E/C review marks. Watch, Under Review, Escalated for Review and Review Closed have explicit next steps. Escalation and closure require notes. The list prioritises escalated accounts. Up to 20 local status changes are retained per account; this is browser storage, not an authenticated audit log, shared case system, report submission or payment intervention. Existing annotations survive the additive currency fields.

Alert Sound has a 0–100% volume control and a Test Sound action. At zero volume it creates no tones. Actual loudness depends on device volume. Two higher tones indicate the documented escalation policy, not proof of crime.
