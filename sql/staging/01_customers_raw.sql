CREATE TABLE IF NOT EXISTS staging.customers_raw(
    customer_number VARCHAR(20),
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    date_of_birth DATE,
    nationality_id INTEGER,
    residence_country_id INTEGER,
    occupation VARCHAR(100),
    annual_income NUMERIC(15,2),
    source_of_funds VARCHAR(255),
    pep_flag BOOLEAN,
    customer_risk_level VARCHAR(20),
    customer_status VARCHAR(20)
);