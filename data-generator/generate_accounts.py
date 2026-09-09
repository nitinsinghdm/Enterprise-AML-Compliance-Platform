import psycopg
import csv
import random
from datetime import date, timedelta

connection = psycopg.connect(
    host="localhost",
    port=5435,
    dbname="northstar_bank",
    user="rdxalpha"
)

# Load existing customers
with connection.cursor() as cursor:
    cursor.execute("""
        SELECT customer_id
        FROM core.customers
    """)

    customers = [row[0] for row in cursor.fetchall()]

print(f"Loaded {len(customers)} customers.")


# Load existing branches
with connection.cursor() as cursor:
    cursor.execute("""
        SELECT branch_id
        FROM reference.branches
    """)

    branches = [row[0] for row in cursor.fetchall()]


# Load existing currencies
with connection.cursor() as cursor:
    cursor.execute("""
        SELECT currency_id, currency_code
        FROM reference.currencies
    """)

    currencies = cursor.fetchall()


account_types = [
    "SAVINGS",
    "CURRENT",
    "BUSINESS",
    "JOINT"
]

account_type_weights = [45, 40, 10, 5]

account_statuses = [
    "ACTIVE",
    "FROZEN",
    "CLOSED",
    "SUSPENDED"
]

account_status_weights = [92, 3, 3, 2]

NUM_ACCOUNTS = 12000

accounts = []

for i in range(1, NUM_ACCOUNTS + 1):

    customer_id = random.choice(customers)

    account_type = random.choices(
        account_types,
        weights=account_type_weights
    )[0]

    account_status = random.choices(
        account_statuses,
        weights=account_status_weights
    )[0]

    branch_id = random.choice(branches)

    currency_id, currency_code = random.choices(
        currencies,
        weights=[60, 10, 5, 5, 5, 3, 2, 2, 2, 2, 2, 2]
    )[0]

    account_number = f"NSB{i:010d}"

    iban = f"DE{random.randint(10, 99)}50010517{account_number}"

    opened_date = date.today() - timedelta(
        days=random.randint(30, 3650)
    )

    closed_date = None

    if account_status == "CLOSED":
        closed_date = opened_date + timedelta(
            days=random.randint(30, 1500)
        )

    if account_type == "SAVINGS":
        overdraft_limit = 0
        interest_rate = round(random.uniform(0.50, 3.50), 2)
        balance = round(random.uniform(500, 50000), 2)

    elif account_type == "CURRENT":
        overdraft_limit = round(
            random.uniform(500, 3000), 2
        )
        interest_rate = round(random.uniform(0.00, 1.50), 2)
        balance = round(
            random.uniform(-overdraft_limit, 15000), 2
        )

    elif account_type == "BUSINESS":
        overdraft_limit = round(
            random.uniform(2000, 10000), 2
        )
        interest_rate = round(random.uniform(0.00, 2.00), 2)
        balance = round(
            random.uniform(-overdraft_limit, 100000), 2
        )

    else:
        overdraft_limit = round(
            random.uniform(0, 1000), 2
        )
        interest_rate = round(random.uniform(0.10, 2.50), 2)
        balance = round(
            random.uniform(0, 30000), 2
        )

    accounts.append(
        (
            account_number,
            customer_id,
            branch_id,
            currency_id,
            iban,
            account_type,
            account_status,
            opened_date,
            closed_date,
            balance,
            overdraft_limit,
            interest_rate
        )
    )

with open("data/accounts.csv", "w", newline="") as file:

    writer = csv.writer(file)

    writer.writerow([
        "account_number",
        "customer_id",
        "branch_id",
        "currency_id",
        "iban",
        "account_type",
        "account_status",
        "opened_date",
        "closed_date",
        "balance",
        "overdraft_limit",
        "interest_rate"
    ])

    writer.writerows(accounts)

print(f"Generated {len(accounts)} accounts.")

connection.close()