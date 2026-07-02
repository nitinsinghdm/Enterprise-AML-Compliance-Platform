# NorthStar Bank Data Dictionary

**Document Version:** 1.0  
**Status:** Approved  
**Last Updated:** July 2026

---

# Overview

The NorthStar Bank Operational Database supports customer onboarding, account management, transaction processing, Anti-Money Laundering (AML), Know Your Customer (KYC), sanctions screening, and compliance analytics.

This document defines the tables, columns, data types, keys, constraints, and business definitions used throughout the operational database.

Version 1.0 documents the Core Banking Domain. Additional domains will be documented as they are implemented.

---

# Core Banking Domain

## Table: customers

### Description

Stores customer identity, demographic information, onboarding details, and AML-related customer attributes.

| Column | Data Type | Key | Nullable | Description |
|---------|-----------|-----|----------|-------------|
| customer_id | UUID | PK | No | Internal unique identifier for each customer. |
| customer_number | VARCHAR(20) | UNIQUE | No | Business-facing customer identifier (e.g., NSB000001). |
| first_name | VARCHAR(100) | | No | Customer first name. |
| last_name | VARCHAR(100) | | No | Customer last name. |
| date_of_birth | DATE | | No | Customer date of birth. |
| nationality_id | INT | FK | No | References `countries.country_id`. |
| residence_country_id | INT | FK | No | References `countries.country_id`. |
| occupation | VARCHAR(100) | | Yes | Customer occupation. |
| annual_income | DECIMAL(15,2) | | Yes | Declared annual income in EUR. |
| source_of_funds | VARCHAR(255) | | Yes | Primary source of customer funds. |
| pep_flag | BOOLEAN | | No | Indicates whether the customer is a Politically Exposed Person (PEP). |
| customer_risk_level | VARCHAR(20) | | No | LOW, MEDIUM, HIGH, CRITICAL. |
| customer_status | VARCHAR(20) | | No | ACTIVE, INACTIVE, BLOCKED, DECEASED, CLOSED. |
| created_at | TIMESTAMP | | No | Record creation timestamp. |
| updated_at | TIMESTAMP | | No | Last record update timestamp. |

### Business Rules

- Every customer must have a unique Customer Number.
- Every customer belongs to exactly one nationality.
- Every customer may have one country of residence.
- A customer may own multiple bank accounts.
- Customer records cannot exist without a unique identifier.
- Customer risk level may change over time.

---

## Table: accounts

### Description

Stores all customer bank accounts.

| Column | Data Type | Key | Nullable | Description |
|---------|-----------|-----|----------|-------------|
| account_id | UUID | PK | No | Internal unique account identifier. |
| account_number | VARCHAR(20) | UNIQUE | No | Internal business account number. |
| customer_id | UUID | FK | No | References `customers.customer_id`. |
| branch_id | INT | FK | No | References `branches.branch_id`. |
| currency_id | INT | FK | No | References `currencies.currency_id`. |
| iban | VARCHAR(34) | UNIQUE | No | International Bank Account Number (IBAN). |
| account_type | VARCHAR(50) | | No | Savings, Current, Business, etc. |
| account_status | VARCHAR(20) | | No | ACTIVE, CLOSED, FROZEN, SUSPENDED. |
| opened_date | DATE | | No | Account opening date. |
| closed_date | DATE | | Yes | Account closure date, if applicable. |
| balance | DECIMAL(18,2) | | No | Current account balance. |
| created_at | TIMESTAMP | | No | Record creation timestamp. |
| updated_at | TIMESTAMP | | No | Last record update timestamp. |

### Business Rules

- Every account belongs to exactly one customer.
- Every account is managed by one branch.
- Every account uses one currency.
- Every account has one unique IBAN.
- Closed accounts remain in the database for historical reporting.

---

## Table: transactions

### Description

Stores all financial transactions performed by customer accounts.

| Column | Data Type | Key | Nullable | Description |
|---------|-----------|-----|----------|-------------|
| transaction_id | UUID | PK | No | Unique transaction identifier. |
| account_id | UUID | FK | No | References `accounts.account_id`. |
| beneficiary_id | UUID | FK | Yes | References `beneficiaries.beneficiary_id`. |
| transaction_type_id | INT | FK | No | References `transaction_types.transaction_type_id`. |
| currency_id | INT | FK | No | References `currencies.currency_id`. |
| country_id | INT | FK | No | References `countries.country_id`. |
| merchant_category_id | INT | FK | Yes | References `merchant_categories.merchant_category_id`. |
| amount | DECIMAL(18,2) | | No | Transaction amount. |
| transaction_direction | VARCHAR(20) | | No | INCOMING or OUTGOING. |
| channel | VARCHAR(30) | | No | ATM, BRANCH, ONLINE, MOBILE, SWIFT, SEPA. |
| payment_reference | VARCHAR(255) | | Yes | Transaction description or payment reference. |
| transaction_status | VARCHAR(20) | | No | PENDING, COMPLETED, FAILED, REVERSED, CANCELLED. |
| transaction_timestamp | TIMESTAMP | | No | Date and time of transaction. |
| created_at | TIMESTAMP | | No | Record creation timestamp. |

### Business Rules

- Every transaction belongs to one account.
- Every transaction has one transaction type.
- Every transaction is recorded in one currency.
- Every transaction occurs in one country.
- Completed transactions must have a timestamp.
- Completed transactions should not be modified.

---

# Relationship Summary

| Parent Table | Child Table | Relationship |
|--------------|------------|--------------|
| countries | customers | One-to-Many |
| customers | accounts | One-to-Many |
| branches | accounts | One-to-Many |
| currencies | accounts | One-to-Many |
| accounts | transactions | One-to-Many |
| countries | transactions | One-to-Many |
| currencies | transactions | One-to-Many |
| transaction_types | transactions | One-to-Many |
| merchant_categories | transactions | One-to-Many |
| beneficiaries | transactions | One-to-Many |

---

# Document Scope

Version 1.0 documents the Core Banking Domain only.

Additional data dictionary entries for Compliance, KYC, Reference Data, External Compliance Data, and Analytics will be added during future implementation phases.