-- ============================================================
-- Enterprise AML Compliance Platform
-- NorthStar Bank Operational Database
-- Script: 01_reference_tables.sql
-- Description: Creates reference tables
-- ============================================================

-- ============================================================
-- Table: countries
-- ============================================================

CREATE TABLE IF NOT EXISTS reference.countries (
    country_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    country_name VARCHAR(100) NOT NULL,
    iso_code CHAR(2) NOT NULL UNIQUE,
    risk_rating VARCHAR(20) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- Table: currencies
-- ============================================================

CREATE TABLE IF NOT EXISTS reference.currencies (
    currency_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    currency_name VARCHAR(50) NOT NULL,
    currency_code CHAR(3) NOT NULL UNIQUE,
    currency_symbol VARCHAR(5) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- Table: branches
-- ============================================================

CREATE TABLE IF NOT EXISTS reference.branches (
    branch_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    branch_code VARCHAR(20) NOT NULL UNIQUE,
    branch_name VARCHAR(100) NOT NULL,
    city VARCHAR(100) NOT NULL,
    country_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_branch_country
        FOREIGN KEY (country_id)
        REFERENCES reference.countries(country_id)
);

-- ============================================================
-- Table: transaction_types
-- ============================================================

CREATE TABLE IF NOT EXISTS reference.transaction_types (
    transaction_type_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    transaction_type_name VARCHAR(50) NOT NULL UNIQUE,
    description VARCHAR(255)
);

-- ============================================================
-- Table: merchant_categories
-- ============================================================

CREATE TABLE IF NOT EXISTS reference.merchant_categories (
    merchant_category_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    merchant_category_name VARCHAR(100) NOT NULL,
    description VARCHAR(255)
);