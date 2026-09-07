from faker import Faker
import csv
import random
from datetime import date

fake = Faker()

NUM_CUSTOMERS = 10000

countries = list(range(1,21))

occupations = [
    "Software Engineer",
    "Accountant",
    "Teacher",
    "Doctor",
    "Nurse",
    "Lawyer",
    "Marketing Manager",
    "Data Analyst",
    "Business Owner",
    "Consultant",
    "Engineer",
    "Sales Manager",
    "Financial Analyst",
    "Architect",
    "Student",
]

sources_of_funds = [
    "SALARY",
    "BUSINESS",
    "INVESTMENTS",
    "INHERITANCE",
    "SAVINGS",
    "PENSION",
]

risk_levels = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]

statuses = ["ACTIVE", "INACTIVE", "BLOCKED", "DECEASED", "CLOSED"]

def generate_customer_number(number):
    return f"NSB{number:06d}"

with open("data/customers.csv", "w", newline="") as file:

    writer = csv.writer(file)

    writer.writerow([
        "customer_number",
        "first_name",
        "last_name",
        "date_of_birth",
        "nationality_id",
        "residence_country_id",
        "occupation",
        "annual_income",
        "source_of_funds",
        "pep_flag",
        "customer_risk_level",
        "customer_status"
    ])

    for i in range(1, NUM_CUSTOMERS + 1):

        first_name = fake.first_name()
        last_name = fake.last_name()

        date_of_birth = fake.date_of_birth(
            minimum_age = 20,
            maximum_age = 85
        )

        nationality_id = random.choice(countries)
        residence_country_id = random.choice(countries)

        occupation = random.choice(occupations)

        income_ranges = {
            "Software Engineer": (45000, 120000),
            "Accountant": (35000, 90000),
            "Teacher": (30000, 70000),
            "Doctor": (60000, 250000),
            "Nurse": (30000, 70000),
            "Lawyer": (50000, 180000),
            "Marketing Manager": (45000, 120000),
            "Data Analyst": (40000, 100000),
            "Business Owner": (30000, 300000),
            "Consultant": (45000, 150000),
            "Engineer": (45000, 120000),
            "Sales Manager": (40000, 130000),
            "Financial Analyst": (45000, 120000),
            "Architect": (40000, 100000),
            "Student": (5000, 35000),
        }

        annual_income = round(
            random.uniform(*income_ranges[occupation]),
            2
        )

        source_of_funds = random.choice(sources_of_funds)

        pep_flag = random.random() < 0.02

        if pep_flag:
            customer_risk_level = random.choices(
                risk_levels,
                weights = [5, 15, 50, 30]
            )[0]
        else:
            customer_risk_level = random.choices(
                risk_levels,
                weights = [60, 30, 8, 2]
            )[0]
        
        customer_status = random.choices(
            statuses,
            weights = [90, 4, 2, 1, 3]
        )[0]

        writer.writerow([
            generate_customer_number(i),
            first_name,
            last_name,
            date_of_birth,
            nationality_id,
            residence_country_id,
            occupation,
            annual_income,
            source_of_funds,
            pep_flag,
            customer_risk_level,
            customer_status
        ])

print(f"Generated {NUM_CUSTOMERS} customers.")