import psycopg

# Environment-only configuration; standard PG* variables remain supported.
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1] / '.env', override=False)
connection = psycopg.connect(os.getenv('DATABASE_URL', ''), connect_timeout=10)

with connection.cursor() as cursor:
    cursor.execute("""
        SELECT customer_id, customer_number
        FROM core.customers
        LIMIT 5;
    """)

    customers = cursor.fetchall()

    for customer in customers:
        print(customer)

connection.close()