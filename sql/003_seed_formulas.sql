-- 003_seed_formulas.sql
-- Seed verified BKI Rules for Hull 2026 calculation formulas.
-- Idempotent: re-running upserts on the unique "code" column.

INSERT INTO formulas
    (code, title, section_no, paragraph_id, page_no, expression, variables, result_unit, notes, verified)
VALUES
('DECK_PLATING_CARGO', 'Lower deck plating thickness for cargo loads', 7, 'B.1.1', 201, '1.21*a*sqrt(pL*k) + tK', '[{"symbol": "a", "name": "Frame spacing", "unit": "m"}, {"symbol": "pL", "name": "Deck load", "unit": "kN/m2"}, {"symbol": "k", "name": "Material factor", "unit": "-"}, {"symbol": "tK", "name": "Corrosion addition", "unit": "mm"}]'::jsonb, 'mm', NULL, true),
('DECK_PLATING_MIN', 'Minimum lower deck plating thickness (2nd deck)', 7, 'B.1.1', 201, '(5.5 + 0.02*L)*sqrt(k)', '[{"symbol": "L", "name": "Rule length", "unit": "m"}, {"symbol": "k", "name": "Material factor", "unit": "-"}]'::jsonb, 'mm', 'L need not be taken greater than 200 m.', true),
('FLOOR_WEB_THICKNESS', 'Floor plate web thickness', 8, 'A.1.2', 208, 'h/100 + 3.0', '[{"symbol": "h", "name": "Web height", "unit": "mm"}]'::jsonb, 'mm', NULL, true),
('FLOOR_PEAK_THICKNESS', 'Floor plate thickness in peaks', 8, 'A.1.2.3', 208, '0.035*L + 5.0', '[{"symbol": "L", "name": "Rule length", "unit": "m"}]'::jsonb, 'mm', NULL, true),
('FLOOR_HEIGHT_FOREPEAK', 'Floor plate height in fore peak', 8, 'A.1.2.3', 208, '0.06*H + 0.7', '[{"symbol": "H", "name": "Moulded depth", "unit": "m"}]'::jsonb, 'm', NULL, true),
('CENTRE_GIRDER_WEB', 'Centre girder web thickness', 8, 'A.2.2.1', 208, '0.07*L + 5.5', '[{"symbol": "L", "name": "Rule length", "unit": "m"}]'::jsonb, 'mm', NULL, true),
('CENTRE_GIRDER_FACEPLATE', 'Centre girder face plate sectional area', 8, 'A.2.2.1', 208, '0.7*L + 12', '[{"symbol": "L", "name": "Rule length", "unit": "m"}]'::jsonb, 'cm2', NULL, true),
('FRAME_SECTION_MODULUS', 'Tween deck / superstructure frame section modulus', 9, 'A.3.2', 227, '0.55*m*a*l**2*p*cr*k', '[{"symbol": "m", "name": "Moment coefficient", "unit": "-"}, {"symbol": "a", "name": "Frame spacing", "unit": "m"}, {"symbol": "l", "name": "Unsupported span", "unit": "m"}, {"symbol": "p", "name": "Load", "unit": "kN/m2"}, {"symbol": "cr", "name": "Curvature factor", "unit": "-"}, {"symbol": "k", "name": "Material factor", "unit": "-"}]'::jsonb, 'cm3', NULL, true),
('WHEEL_LOAD', 'Wheel load on deck plate panel', 7, 'B.2.1', 201, '(Q/n)*(1 + av)', '[{"symbol": "Q", "name": "Axle load", "unit": "kN"}, {"symbol": "n", "name": "Number of wheels per axle", "unit": "-"}, {"symbol": "av", "name": "Acceleration factor", "unit": "-", "required": false, "default": 0}]'::jsonb, 'kN', NULL, true),
('FORECASTLE_SPEED', 'Forecastle frame speed threshold', 9, 'A.3.1', 227, '1.6*sqrt(L)', '[{"symbol": "L", "name": "Rule length", "unit": "m"}]'::jsonb, 'kn', NULL, true)
ON CONFLICT (code) DO UPDATE SET
    title = EXCLUDED.title,
    section_no = EXCLUDED.section_no,
    paragraph_id = EXCLUDED.paragraph_id,
    page_no = EXCLUDED.page_no,
    expression = EXCLUDED.expression,
    variables = EXCLUDED.variables,
    result_unit = EXCLUDED.result_unit,
    notes = EXCLUDED.notes,
    verified = EXCLUDED.verified;