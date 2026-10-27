-- Additive migration: no changes to the existing operational tables or seed files.
CREATE TABLE IF NOT EXISTS staging.ingestion_batches (
    batch_id UUID PRIMARY KEY,
    entity TEXT NOT NULL,
    source_name TEXT NOT NULL,
    source_sha256 TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ,
    accepted INTEGER NOT NULL DEFAULT 0,
    rejected INTEGER NOT NULL DEFAULT 0,
    replayed INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS staging.ingestion_rows (
    batch_id UUID REFERENCES staging.ingestion_batches(batch_id),
    row_number INTEGER NOT NULL,
    payload JSONB NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('ACCEPTED','REJECTED','REPLAYED')),
    reason TEXT,
    PRIMARY KEY(batch_id, row_number)
);
CREATE INDEX IF NOT EXISTS idx_transactions_account_time ON core.transactions(account_id, transaction_timestamp);
CREATE INDEX IF NOT EXISTS idx_accounts_customer ON core.accounts(customer_id);
CREATE INDEX IF NOT EXISTS idx_beneficiaries_customer ON core.beneficiaries(customer_id);
