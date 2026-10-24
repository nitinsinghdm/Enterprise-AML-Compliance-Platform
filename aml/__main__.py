import argparse
import json
from pathlib import Path

from .db import ROOT, bootstrap, connect


def main():
    parser = argparse.ArgumentParser(description='NorthStar synthetic AML pipeline')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('validate', help='Run read-only SQL data quality checks')
    sub.add_parser('init', help='Apply additive migrations and seed an empty reference database')
    demo = sub.add_parser('demo', help='Generate and ingest reproducible synthetic master data and transactions')
    demo.add_argument('--customers', type=int, default=200)
    demo.add_argument('--output', default='data/generated')
    demo.add_argument('--seed', type=int, default=42)
    demo.add_argument('--per-account', type=int, default=30)
    demo.add_argument('--start', default='2026-01-01')
    gen = sub.add_parser('generate', help='Generate transactions against existing active accounts')
    gen.add_argument('--output', default='data/generated')
    gen.add_argument('--seed', type=int, default=42)
    gen.add_argument('--per-account', type=int, default=30)
    gen.add_argument('--start', default='2026-01-01')
    ingest = sub.add_parser('ingest')
    ingest.add_argument('entity', choices=['customers', 'accounts', 'beneficiaries', 'transactions'])
    ingest.add_argument('path')
    export = sub.add_parser('export')
    export.add_argument('--output', default='data/gold/export')
    train = sub.add_parser('train')
    train.add_argument('--features', default='data/gold/export/customer_features.csv')
    train.add_argument('--labels', default='data/generated/scenario_labels.csv')
    train.add_argument('--output', default='data/gold/export')
    train.add_argument('--seed', type=int, default=42)
    predict = sub.add_parser('predict')
    predict.add_argument('--features', required=True)
    predict.add_argument('--model', required=True)
    predict.add_argument('--output', required=True)
    spark = sub.add_parser('spark')
    spark.add_argument('--source', default='data/gold/export/transaction_facts.csv')
    spark.add_argument('--output', default='data/spark')
    spark.add_argument('--master', default='local[2]')
    warehouse = sub.add_parser('warehouse')
    warehouse.add_argument('--source', default='data/gold/export')
    args = parser.parse_args()
    if args.command == 'train':
        from .model import train
        result = train(args.features, args.labels, args.output, args.seed)
    elif args.command == 'predict':
        from .model import predict
        result = predict(args.features, args.model, args.output)
    elif args.command == 'spark':
        from .spark import run
        result = run(args.source, args.output, args.master)
    elif args.command == 'warehouse':
        from .warehouse import load
        result = load(args.source)
    else:
        with connect() as conn:
            if args.command == 'validate':
                checks = conn.execute((ROOT / 'sql/tests/02_pipeline_validation.sql').read_text()).fetchall()
                result = {'checks': checks, 'violations': sum(r['violations'] for r in checks)}
            elif args.command == 'init':
                bootstrap(conn)
                result = {'status': 'initialized'}
            elif args.command in ('demo', 'generate'):
                from .generate import demo_entities, transactions
                from .ingest import ingest
                result = {}
                if args.command == 'demo':
                    bootstrap(conn)
                    result['entities'] = demo_entities(conn, args.output, args.customers, args.seed)
                result['generation'] = transactions(conn, args.output, args.seed, args.per_account, args.start)
                if args.command == 'demo':
                    result['ingestion'] = ingest(conn, 'transactions', Path(args.output) / 'transactions.csv')
            elif args.command == 'ingest':
                from .ingest import ingest
                result = ingest(conn, args.entity, args.path)
            elif args.command == 'export':
                from .export import export
                result = export(conn, args.output)
    print(json.dumps(result, indent=2, default=str))
    if result.get('violations', 0) or result.get('rejected', 0) or result.get('ingestion', {}).get('rejected', 0):
        raise SystemExit(2)


if __name__ == '__main__':
    main()
