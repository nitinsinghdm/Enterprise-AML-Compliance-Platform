"""Package a small synthetic-only summary preview; never transaction rows or customer PII."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aml.dashboard_data import EXPORT, OPTIONAL, PREVIEW, REQUIRED, load_snapshot

parser = argparse.ArgumentParser()
parser.add_argument('--synthetic-data-confirmed', action='store_true', required=True)
args = parser.parse_args()
snapshot = load_snapshot('My local exports', EXPORT)
payload = {'provenance':'Synthetic 100-customer NorthStar fixture, seed 42; 2,110 transactions. Summary rows only.',
           'manifest':snapshot['manifest'], 'metrics':snapshot['metrics'], 'datasets':{}}
for name in {**REQUIRED, **OPTIONAL}:
    frame = snapshot['frames'][name]
    payload['datasets'][name] = json.loads(frame.to_json(orient='records', date_format='iso'))
PREVIEW.parent.mkdir(parents=True,exist_ok=True)
PREVIEW.write_text(json.dumps(payload,separators=(',',':')))
print(f'Wrote {PREVIEW.stat().st_size:,} bytes of synthetic summary data')
