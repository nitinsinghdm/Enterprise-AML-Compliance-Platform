import psycopg
import random
import csv

connection = psycopg.connect(
    host="localhost",
    port=5435,
    dbname="northstar_bank",
    user="rdxalpha"
)

# Load customers
with connection.cursor() as cursor:
    cursor.execute("""
        SELECT customer_id
        FROM core.customers
    """)

    customers = [row[0] for row in cursor.fetchall()]

# Load countries
with connection.cursor() as cursor:
    cursor.execute("""
        SELECT country_id
        FROM reference.countries
    """)

    countries = [row[0] for row in cursor.fetchall()]

print(f"Loaded {len(customers)} customers.")
print(f"Loaded {len(countries)} countries.")

NUM_BENEFICIARIES = 18000

bank_names = [
    "Deutsche Bank",
    "Commerzbank",
    "UniCredit Bank",
    "ING Germany",
    "Santander Germany",
    "BNP Paribas",
    "HSBC",
    "Barclays",
    "JPMorgan Chase",
    "Citibank",
]

bank_codes = [
    "DEUTDEFF",
    "COBADEFF",
    "HYVEDEMM",
    "INGDDEFF",
    "SCFBDE33",
    "BNPAFRPP",
    "HBUKGB4B",
    "BARCGB22",
    "CHASUS33",
    "CITIUS33",
]

statuses = ["ACTIVE", "INACTIVE"]
status_weights = [85, 15]

beneficiaries = []

for i in range(1, NUM_BENEFICIARIES + 1):

    customer_id = random.choice(customers)

    beneficiary_name = (
        f"{random.choice(['Alex', 'Chris', 'Sam', 'Jordan', 'Taylor', 'Morgan', 'Daniel', 'Sarah'])} "
        f"{random.choice(['Smith', 'Miller', 'Schmidt', 'Brown', 'Wilson', 'Martin', 'Taylor', 'Anderson'])}"
    )

    beneficiary_account_number = f"BEN{i:014d}"

    beneficiary_bank_name, beneficiary_bank_code = random.choice(
        list(zip(bank_names, bank_codes))
    )

    beneficiary_country_id = random.choice(countries)

    beneficiary_iban = (
        f"DE89{beneficiary_account_number[:18]}"
    )

    beneficiary_status = random.choices(
        statuses,
        weights=status_weights
    )[0]

    beneficiaries.append(
        (
            customer_id,
            beneficiary_name,
            beneficiary_account_number,
            beneficiary_iban,
            beneficiary_bank_code,
            beneficiary_bank_name,
            beneficiary_country_id,
            beneficiary_status
        )
    )


with open("data/beneficiaries.csv", "w", newline="") as file:

    writer = csv.writer(file)

    writer.writerow([
        "customer_id",
        "beneficiary_name",
        "beneficiary_account_number",
        "beneficiary_iban",
        "beneficiary_bank_code",
        "beneficiary_bank_name",
        "beneficiary_country_id",
        "beneficiary_status"
    ])

    writer.writerows(beneficiaries)


print(f"Generated {len(beneficiaries)} beneficiaries.")

connection.close()