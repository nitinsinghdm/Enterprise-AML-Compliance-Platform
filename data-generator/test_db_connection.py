import psycopg

connection = psycopg.connect(
    host="localhost",
    port=5435,
    dbname="northstar_bank",
    user="rdxalpha"
)

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