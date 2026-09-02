-- ============================================================
-- Seed Data: Currencies
-- ============================================================

TRUNCATE TABLE reference.currencies RESTART IDENTITY CASCADE;

INSERT INTO reference.currencies(
    currency_name,
    currency_code,
    currency_symbol
)

VALUES
('Euro', 'EUR', '€'),
('US Dollar', 'USD', '$'),
('British Pound', 'GBP', '£'),
('Swiss Franc', 'CHF', 'CHF'),
('Indian Rupee', 'INR', '₹'),
('Japanese Yen', 'JPY', '¥'),
('Chinese Yuan', 'CNY', '¥'),
('Canadian Dollar', 'CAD', 'C$'),
('Australian Dollar', 'AUD', 'A$'),
('UAE Dirham', 'AED', 'AED'),
('Polish Zloty', 'PLN', 'zł'),
('Swedish Krona', 'SEK', 'kr');