-- ============================================================
-- Seed Data: Branches
-- ============================================================

TRUNCATE TABLE reference.branches RESTART IDENTITY CASCADE;

INSERT INTO reference.branches (
    branch_code,
    branch_name,
    city,
    country_id
)

VALUES
('BER001', 'Berlin Mitte',            'Berlin',      1),
('BER002', 'Berlin Charlottenburg',   'Berlin',      1),
('MUC001', 'Munich Central',          'Munich',      1),
('FRA001', 'Frankfurt Financial District', 'Frankfurt', 1),
('HAM001', 'Hamburg Harbour',         'Hamburg',     1),
('CGN001', 'Cologne City',            'Cologne',     1),
('STR001', 'Stuttgart Centre',        'Stuttgart',   1),
('DUS001', 'Düsseldorf Central',      'Düsseldorf',  1),
('LEJ001', 'Leipzig City',            'Leipzig',     1),
('DRS001', 'Dresden Centre',          'Dresden',     1);