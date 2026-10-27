"""Read-only dashboard snapshots. Never connects to a database or reads credentials."""
import hashlib
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PREVIEW = ROOT / 'dashboard/preview/snapshot.json'
EXPORT = ROOT / 'data/gold/export'
REQUIRED = {
    'dashboard_daily': ['transaction_date','destination_country','channel','transaction_count','completed_count','completed_amount_eur','cross_border_count'],
    'alerts': ['customer_id','account_id','transaction_date','rule_code','evidence_count','amount_eur'],
    'customer_features': ['customer_id','transaction_count','total_amount_eur','mean_amount_eur','max_amount_eur','cross_border_ratio','high_risk_country_ratio','near_threshold_cash_count','max_daily_count','pep_flag'],
}
OPTIONAL = {
    'customer_risk_scores': ['customer_id','risk_score','risk_band','model_version','evaluation_split'],
    'pipeline_batches': ['batch_id','entity','started_at','finished_at','accepted','rejected','replayed'],
    'quality_checks': ['check_name','violations'],
}


def load_snapshot(mode='Bundled preview', directory=None):
    frames, warnings = {}, []
    if mode == 'Bundled preview':
        raw = json.loads(PREVIEW.read_text())
        manifest, metrics = raw['manifest'], raw.get('metrics', {})
        for name, fields in {**REQUIRED, **OPTIONAL}.items():
            frames[name] = pd.DataFrame(raw['datasets'].get(name, []), columns=fields)
    else:
        directory = Path(directory or EXPORT)
        manifest = json.loads((directory / 'manifest.json').read_text())
        metrics_path = directory / 'metrics.json'
        metrics = json.loads(metrics_path.read_text()) if metrics_path.exists() else {}
        for name, fields in {**REQUIRED, **OPTIONAL}.items():
            path = directory / f'{name}.csv'
            if not path.exists():
                if name in REQUIRED:
                    raise ValueError(f'Missing {name}.csv. Run python -m aml export.')
                frames[name] = pd.DataFrame(columns=fields)
                continue
            expected = manifest.get('datasets', {}).get(name)
            if expected and hashlib.sha256(path.read_bytes()).hexdigest() != expected['sha256']:
                raise ValueError(f'{name}.csv differs from its manifest. Finish a fresh export before reloading.')
            frame = pd.read_csv(path)
            if not set(fields) <= set(frame.columns):
                raise ValueError(f'Unexpected columns in {name}.csv.')
            if expected and len(frame) != expected['rows']:
                raise ValueError(f'Row count mismatch in {name}.csv.')
            frames[name] = frame[fields]
        scores_path = directory / 'customer_risk_scores.csv'
        if scores_path.exists():
            # Training outputs are not part of the database export transaction.
            from datetime import datetime
            exported = datetime.fromisoformat(manifest['exported_at']).timestamp()
            if scores_path.stat().st_mtime < exported:
                warnings.append('Risk scores predate this export. Run python -m aml train to refresh them.')
    for name in ('dashboard_daily', 'alerts'):
        frames[name]['transaction_date'] = pd.to_datetime(frames[name]['transaction_date']).dt.date
    return {'frames': frames, 'manifest': manifest, 'metrics': metrics, 'warnings': warnings}


def filter_activity(frame, countries, channels, dates):
    selected = frame[frame.destination_country.isin(countries) & frame.channel.isin(channels)]
    if len(dates) == 2:
        selected = selected[selected.transaction_date.between(*dates)]
    return selected


def activity_metrics(frame):
    total = int(frame.transaction_count.sum())
    completed = int(frame.completed_count.sum())
    return dict(total=total, completed=completed, volume=float(frame.completed_amount_eur.sum()),
                completion_rate=completed / total * 100 if total else 0)
