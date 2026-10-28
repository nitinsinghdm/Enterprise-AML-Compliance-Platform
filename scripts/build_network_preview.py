"""Create a public network preview from a dedicated synthetic demo database."""
import argparse
from pathlib import Path
from aml.db import connect
from aml.network import write_snapshot

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--synthetic-data-confirmed', action='store_true', required=True)
parser.add_argument('--output', type=Path, default=Path('web/network/data.json'))
args = parser.parse_args()
with connect() as conn:
    print(write_snapshot(conn, args.output, synthetic_data_confirmed=args.synthetic_data_confirmed))
