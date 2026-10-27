-- ============================================================
-- Seed Data: Merchant Categories
-- ============================================================

TRUNCATE TABLE reference.merchant_categories RESTART IDENTITY CASCADE;

INSERT INTO reference.merchant_categories (
    merchant_category_name,
    description
)
VALUES
('GROCERY', 'Supermarkets and grocery stores'),
('RESTAURANT', 'Restaurants, cafes, and food services'),
('FUEL', 'Petrol stations and fuel purchases'),
('HEALTHCARE', 'Hospitals, clinics, and medical services'),
('PHARMACY', 'Pharmacies and prescription-related purchases'),
('TRAVEL', 'Airlines, travel agencies, and transportation'),
('HOTEL', 'Hotels and accommodation services'),
('ELECTRONICS', 'Consumer electronics and technology retailers'),
('UTILITIES', 'Electricity, water, gas, and other utility payments'),
('ENTERTAINMENT', 'Cinema, events, gaming, and entertainment'),
('EDUCATION', 'Schools, universities, and educational services'),
('INSURANCE', 'Insurance companies and insurance payments'),
('GOVERNMENT', 'Government services and public-sector payments'),
('RETAIL', 'General retail and department stores'),
('ONLINE_SERVICES', 'Online platforms and digital services'),
('TELECOMMUNICATIONS', 'Mobile, internet, and telecommunications services'),
('PROFESSIONAL_SERVICES', 'Legal, accounting, consulting, and professional services'),
('REAL_ESTATE', 'Property-related payments and real estate services'),
('CHARITY', 'Charitable organizations and donations'),
('CASH_WITHDRAWAL', 'Cash withdrawals and ATM-related transactions');