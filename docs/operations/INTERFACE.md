# Using the NorthStar interface

## Start with a guided tour

1. Install `requirements-dashboard.txt` and run `streamlit run dashboard_app.py` from the repository root.
2. Open http://localhost:8501. Select **Bundled preview** to explore without PostgreSQL.
3. On **Overview**, examine the payment-volume spike and the rule counts. Expand Filter activity and change country/channel/date; the four activity metrics and two activity charts update. Monitoring signals deliberately remain whole-snapshot counts and are labeled that way.
4. Open **Alert explorer**, select a rule and inspect an individual alert. Read its explanation and the associated customer behavior features. No case-management decision is saved.
5. Open **Customer risk**, choose holdout and examine the 25 unseen customers in the preview. Scores on training rows are not evaluation evidence.
6. Open **Pipeline & guide** to read how the original schema connects to the new work. Inspect the actual load batches and SQL check results captured at export time.

## See your own run

Configure a dedicated demo database using SETUP.md. Run demo → validate → export → train in a terminal. These commands print their results. Then select **My local exports** in the interface and click **Reload snapshot**. The dashboard reads `data/gold/export` and never opens `.env`, starts subprocesses or connects to PostgreSQL/Snowflake.

This is snapshot monitoring, not a live job scheduler. It does not claim that Spark or a cloud connection is healthy just because code exists. Cloud stages are explicitly marked unverified by the viewer. A missing local export shows an actionable message; an altered CSV with a manifest checksum is rejected. Older exports without batch/quality files remain readable but show that evidence as unavailable. Model outputs are optional; regenerate them after each new export. The UI warns when score-file modification time is older than the export timestamp (a useful check, not cryptographic model lineage).

The server binds to localhost by default. This app has no authentication or multiuser authorization; do not change the bind address for public deployment without adding those controls.

## Bundled preview provenance

`dashboard/preview/snapshot.json` is approximately 65 KB. It was generated from the synthetic 100-customer, seed-42 demonstration (20 baseline transactions per account plus injected scenarios). It contains daily activity, alert groups, customer aggregate features/scores, load summaries, quality results and evaluation metadata. No raw transaction records, labels, names, addresses, birth dates or account numbers are packaged.

The manifest retains source snapshot counts and hashes for provenance; they refer to the original CSVs, not the embedded JSON serialization. Regenerate only from known synthetic input:

```sh
python -m aml export
python -m aml train
python scripts/build_dashboard_preview.py --synthetic-data-confirmed
```

The preview is fixed test data. If replacing it with another fixture, update its provenance and the corresponding expected totals in tests/documentation. Do not package actual customer data into a public repository.

## Screenshots

README screenshots are actual browser captures of the bundled preview, not design mockups. Start the dashboard, then optionally install the screenshot tools:

```sh
pip install playwright==1.55.0
python -m playwright install chromium
python scripts/capture_dashboard.py
```

The screenshot script saves the Overview and Alert explorer pages to `images/`. `images/pipeline.svg` is an editable diagram. UI tests use Streamlit AppTest; browser captures additionally check the rendered appearance.
