-- ============================================================
-- Enterprise AML Compliance Platform
-- NorthStar Bank Operational Database
-- Script: 02_core_tables.sql
-- Description: Creates core banking tables
-- ============================================================

-- ============================================================
-- Table: Customers
-- ============================================================

CREATE TABLE IF NOT EXISTS core.customers (
    customer_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_number VARCHAR(20) UNIQUE NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    date_of_birth DATE NOT NULL,
    nationality_id INT NOT NULL,
    residence_country_id INT NOT NULL,
    occupation VARCHAR(100),
    annual_income DECIMAL(15,2),
    source_of_funds VARCHAR(255),
    pep_flag BOOLEAN NOT NULL,
    customer_risk_level VARCHAR(20) NOT NULL
        CHECK(customer_risk_level IN ('LOW','MEDIUM','HIGH','CRITICAL')),
    customer_status VARCHAR(20) NOT NULL
        CHECK(customer_status IN('ACTIVE', 'INACTIVE', 'BLOCKED','DECEASED','CLOSED')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_customer_nationality
        FOREIGN KEY (nationality_id)
        REFERENCES reference.countries(country_id),
    CONSTRAINT fk_customer_residence
        FOREIGN KEY (residence_country_id)
        REFERENCES reference.countries(country_id)
);

-- ============================================================
-- Table: Account
-- ============================================================

CREATE TABLE IF NOT EXISTS core.accounts (
    account_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_number VARCHAR(20) UNIQUE NOT NULL,
    customer_id UUID NOT NULL,
    branch_id INT NOT NULL,
    currency_id INT NOT NULL,
    iban VARCHAR(34) UNIQUE NOT NULL,
    account_type VARCHAR(50) NOT NULL
        CHECK (account_type IN('SAVINGS', 'CURRENT', 'BUSINESS', 'JOINT')),
    account_status VARCHAR(20) NOT NULL
        CHECK (account_status IN('ACTIVE', 'FROZEN', 'CLOSED', 'SUSPENDED')),
    opened_date DATE NOT NULl,
    closed_date DATE,
    balance DECIMAL(18,2) NOT NULL DEFAULT 0.00,
    overdraft_limit DECIMAL(18,2) NOT NULL DEFAULT 0.00,
    interest_rate DECIMAL(5,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_customers
        FOREIGN KEY (customer_id)
        REFERENCES core.customers(customer_id),
    CONSTRAINT fk_branches
        FOREIGN KEY (branch_id)
        REFERENCES reference.branches(branch_id),
    CONSTRAINT fk_currencies
        FOREIGN KEY (currency_id)
        REFERENCES reference.currencies(currency_id)
);

-- ============================================================
-- Table: beneficiaries
-- ============================================================

CREATE TABLE IF NOT EXISTS core.beneficiaries (
    beneficiary_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL,
    beneficiary_name VARCHAR(150) NOT NULL,
    beneficiary_account_number VARCHAR(34) UNIQUE NOT NULL,
    beneficiary_iban VARCHAR(34),
    beneficiary_bank_code VARCHAR(20),
    beneficiary_bank_name VARCHAR(100) NOT NULL,
    beneficiary_country_id INT NOT NULL,
    beneficiary_status VARCHAR(20) NOT NULL
        CHECK ( beneficiary_status IN ('ACTIVE', 'INACTIVE')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_beneficiary_customer
        FOREIGN KEY (customer_id)
        REFERENCES core.customers(customer_id),
    CONSTRAINT fk_beneficiary_country
        FOREIGN KEY (beneficiary_country_id)
        REFERENCES reference.countries(country_id)
);

-- ============================================================
-- Table: Transactions
-- ============================================================

CREATE TABLE IF NOT EXISTS core.transactions (
    transaction_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID NOT NULL,
    beneficiary_id UUID,
    transaction_type_id INT NOT NULL,
    currency_id INT NOT NULL,
    exchange_rate DECIMAL(12,6),
    country_id INT NOT NULL,
    merchant_category_id INT,
    amount DECIMAL(18,2) NOT NULL CHECK (amount > 0),
    transaction_direction VARCHAR(20) NOT NULL
        CHECK (transaction_direction IN ('OUTGOING', 'INCOMING')),
    channel VARCHAR(30) NOT NULL
        CHECK (channel IN ('ATM', 'BRANCH', 'ONLINE', 'MOBILE', 'SWIFT', 'SEPA')),
    payment_reference VARCHAR(255),
    transaction_status VARCHAR(20) NOT NULL
        CHECK (transaction_status IN ('PENDING', 'COMPLETED', 'FAILED', 'REVERSED', 'CANCELLED')),
    transaction_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_accounts
        FOREIGN KEY (account_id)
        REFERENCES core.accounts (account_id),
    CONSTRAINT fk_beneficiaries
        FOREIGN KEY (beneficiary_id)
        REFERENCES core.beneficiaries(beneficiary_id),
    CONSTRAINT fk_transaction_types
        FOREIGN KEY (transaction_type_id)
        REFERENCES reference.transaction_types (transaction_type_id),
    CONSTRAINT fk_currencies
        FOREIGN KEY (currency_id)
        REFERENCES reference.currencies (currency_id),
    CONSTRAINT fk_countries
        FOREIGN KEY (country_id)
        REFERENCES reference.countries (country_id),
    CONSTRAINT fk_merchant_categories
        FOREIGN KEY (merchant_category_id)
        REFERENCES reference.merchant_categories (merchant_category_id)
);