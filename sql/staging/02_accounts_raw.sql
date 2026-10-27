CREATE TABLE IF NOT EXISTS staging.accounts_raw (
    account_number VARCHAR(20),
    customer_id UUID,
    branch_id INTEGER,
    currency_id INTEGER,
    iban VARCHAR(34),
    account_type VARCHAR(50),
    account_status VARCHAR(20),
    opened_date DATE,
    closed_date DATE,
    balance NUMERIC(18,2),
    overdraft_limit NUMERIC(18,2),
    interest_rate NUMERIC(5,2)
);