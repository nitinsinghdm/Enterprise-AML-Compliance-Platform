-- ============================================================
-- Seed Data: Countries
-- ============================================================

TRUNCATE TABLE reference.countries RESTART IDENTITY CASCADE;

INSERT INTO reference.countries (
    country_name,
    iso_code,
    risk_rating
)

VALUES
('Germany', 'DE', 'LOW'),
('France', 'FR', 'LOW'),
('Netherlands', 'NL', 'LOW'),
('Belgium', 'BE', 'LOW'),
('Switzerland', 'CH', 'LOW'),
('Austria', 'AT', 'LOW'),
('Spain', 'ES', 'LOW'),
('Italy', 'IT', 'LOW'),
('Poland', 'PL', 'LOW'),
('United Kingdom', 'GB', 'LOW'),
('United States', 'US', 'LOW'),
('Canada', 'CA', 'LOW'),
('Australia', 'AU', 'LOW'),
('Japan', 'JP', 'LOW'),
('India', 'IN', 'MEDIUM'),
('Singapore', 'SG', 'LOW'),
('United Arab Emirates', 'AE', 'MEDIUM'),
('Brazil', 'BR', 'MEDIUM'),
('China', 'CN', 'HIGH'),
('Russia', 'RU', 'HIGH');