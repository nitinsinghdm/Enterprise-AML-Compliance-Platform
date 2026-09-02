-- ============================================================
-- Seed Data: Transaction Types
-- ============================================================

TRUNCATE TABLE reference.transaction_types RESTART IDENTITY CASCADE;

INSERT INTO reference.transaction_types (
    transaction_type_name,
    description
)
VALUES
('DEPOSIT', 'Cash or electronic funds deposited into an account'),
('WITHDRAWAL', 'Funds withdrawn from an account'),
('TRANSFER', 'Transfer of funds between accounts'),
('CARD_PAYMENT', 'Payment made using a debit or credit card'),
('DIRECT_DEBIT', 'Automated payment collected from an account'),
('STANDING_ORDER', 'Scheduled recurring payment from an account'),
('INTERNATIONAL_TRANSFER', 'Cross-border transfer of funds'),
('ATM_WITHDRAWAL', 'Cash withdrawal performed at an ATM'),
('CASH_DEPOSIT', 'Cash deposited at a branch or cash deposit facility'),
('BANK_FEE', 'Fee charged by the bank for a service or transaction'),
('INTEREST', 'Interest credited to or charged against an account'),
('REFUND', 'Funds returned to an account following a previous payment');