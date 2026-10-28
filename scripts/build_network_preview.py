"""Build the public synthetic network in a new disposable database, then remove it."""
import argparse
import tempfile
from pathlib import Path
from uuid import uuid4
import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from aml.db import connect
from aml.network import write_snapshot
from aml.network_fixture import populate

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--synthetic-data-confirmed',action='store_true',required=True)
parser.add_argument('--output',type=Path,default=Path('web/network/data.json'))
args=parser.parse_args()
with connect() as admin:
    name='aml_network_fixture_'+uuid4().hex[:10]
    admin.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
    try:
        params=admin.info.get_parameters();params['dbname']=name
        # get_parameters omits passwords; retain authentication only in memory.
        params['password']=admin.info.password
        with psycopg.connect(**params,autocommit=True,row_factory=dict_row) as conn, tempfile.TemporaryDirectory() as directory:
            populate(conn,Path(directory))
            print(write_snapshot(conn,args.output,synthetic_data_confirmed=args.synthetic_data_confirmed))
    finally:
        admin.execute(sql.SQL('DROP DATABASE {} WITH (FORCE)').format(sql.Identifier(name)))
