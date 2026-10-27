"""Export a consistent snapshot without names, IBANs or payment references."""
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

DATASETS = {
    'transaction_facts': 'SELECT * FROM analytics.transaction_facts ORDER BY transaction_id',
    'customer_features': 'SELECT * FROM analytics.customer_features ORDER BY customer_id',
    'dashboard_daily': 'SELECT * FROM analytics.dashboard_daily ORDER BY transaction_date,destination_country,channel',
    'alerts': 'SELECT * FROM analytics.aml_alerts ORDER BY customer_id,account_id,transaction_date,rule_code',
}


def export(conn, directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    manifest = {'exported_at': datetime.now(timezone.utc).isoformat(), 'base_currency': 'EUR', 'datasets': {}}
    with conn.transaction():
        conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')
        for name, query in DATASETS.items():
            path = directory / f'{name}.csv'
            with conn.cursor(name=f'export_{name}') as cur, path.open('w', newline='', encoding='utf-8') as f:
                cur.execute(query)
                # Named cursors populate description after their first fetch.
                first = cur.fetchone()
                fields = [c.name for c in cur.description]
                writer = csv.DictWriter(f, fieldnames=fields)
                writer.writeheader()
                count = 0
                if first:
                    writer.writerow(first)
                    count += 1
                for row in cur:
                    writer.writerow(row)
                    count += 1
            with path.open('rb') as f:
                digest = hashlib.file_digest(f, 'sha256').hexdigest()
            manifest['datasets'][name] = {'rows': count, 'sha256': digest}
    (directory / 'manifest.json').write_text(json.dumps(manifest, indent=2))
    return manifest
