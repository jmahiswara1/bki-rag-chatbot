-- Migration: Add Shell Plating Formulas (Section 6)
-- Adds 4 formulas for bottom and side shell plating, addressing L < 90m and L >= 90m branches.

INSERT INTO public.formulas (code, title, section_no, paragraph_id, page_no, expression, variables, result_unit, notes, verified)
VALUES
(
    'BOTTOM_PLATING_L_LESS_90',
    'Bottom shell plating thickness (L < 90m)',
    6, 'B.1.1', 167,
    '1.9 * nf * a * sqrt(pB * k) + tK',
    jsonb_build_array(
        jsonb_build_object('symbol', 'L', 'name', 'Length of ship', 'unit', 'm', 'required', true),
        jsonb_build_object('symbol', 'pB', 'name', 'Bottom load', 'unit', 'kN/m2', 'required', true),
        jsonb_build_object('symbol', 'a', 'name', 'Stiffener spacing', 'unit', 'm', 'required', true),
        jsonb_build_object('symbol', 'k', 'name', 'Material factor', 'unit', '', 'required', true, 'default', 1.0),
        jsonb_build_object('symbol', 'nf', 'name', 'Framing factor', 'unit', '', 'required', true, 'default', 1.0),
        jsonb_build_object('symbol', 'tK', 'name', 'Corrosion addition', 'unit', 'mm', 'required', true, 'default', 1.5)
    ),
    'mm',
    'L < 90m. For mild steel, k=1.0. nf=1.0 for transverse, 0.83 for longitudinal framing. tK is generally 1.5mm.',
    true
),
(
    'BOTTOM_PLATING_L_GREATER_90',
    'Bottom shell plating thickness (L >= 90m)',
    6, 'B.1.2', 167,
    'Max(18.3 * nf * a * sqrt(pB / (200.2/k)) + tK, 1.21 * a * sqrt(pB * k) + tK)',
    jsonb_build_array(
        jsonb_build_object('symbol', 'L', 'name', 'Length of ship', 'unit', 'm', 'required', true),
        jsonb_build_object('symbol', 'pB', 'name', 'Bottom load', 'unit', 'kN/m2', 'required', true),
        jsonb_build_object('symbol', 'a', 'name', 'Stiffener spacing', 'unit', 'm', 'required', true),
        jsonb_build_object('symbol', 'k', 'name', 'Material factor', 'unit', '', 'required', true, 'default', 1.0),
        jsonb_build_object('symbol', 'nf', 'name', 'Framing factor', 'unit', '', 'required', true, 'default', 1.0),
        jsonb_build_object('symbol', 'tK', 'name', 'Corrosion addition', 'unit', 'mm', 'required', true, 'default', 1.5)
    ),
    'mm',
    'L >= 90m. The expression simplifies σpℓ to 200.2/k deterministically for bottom plating. Result is the maximum of tB1 and tB2.',
    true
),
(
    'SIDE_PLATING_L_LESS_90',
    'Side shell plating thickness (L < 90m)',
    6, 'C.1.1', 170,
    '1.9 * nf * a * sqrt(pS * k) + tK',
    jsonb_build_array(
        jsonb_build_object('symbol', 'L', 'name', 'Length of ship', 'unit', 'm', 'required', true),
        jsonb_build_object('symbol', 'pS', 'name', 'Side load', 'unit', 'kN/m2', 'required', true),
        jsonb_build_object('symbol', 'a', 'name', 'Stiffener spacing', 'unit', 'm', 'required', true),
        jsonb_build_object('symbol', 'k', 'name', 'Material factor', 'unit', '', 'required', true, 'default', 1.0),
        jsonb_build_object('symbol', 'nf', 'name', 'Framing factor', 'unit', '', 'required', true, 'default', 1.0),
        jsonb_build_object('symbol', 'tK', 'name', 'Corrosion addition', 'unit', 'mm', 'required', true, 'default', 1.5)
    ),
    'mm',
    'L < 90m. For mild steel, k=1.0. nf=1.0 for transverse, 0.83 for longitudinal framing. tK is generally 1.5mm.',
    true
),
(
    'SIDE_PLATING_L_GREATER_90',
    'Side shell plating thickness (L >= 90m)',
    6, 'C.1.2', 170,
    'Max(18.3 * nf * a * sqrt(pS / (176.1/k)) + tK, 1.21 * a * sqrt(pS * k) + tK, 18.3 * nf * a * sqrt(pS1 / (190.8/k)) + tK)',
    jsonb_build_array(
        jsonb_build_object('symbol', 'L', 'name', 'Length of ship', 'unit', 'm', 'required', true),
        jsonb_build_object('symbol', 'pS', 'name', 'Side load', 'unit', 'kN/m2', 'required', true),
        jsonb_build_object('symbol', 'pS1', 'name', 'Side load 1', 'unit', 'kN/m2', 'required', true),
        jsonb_build_object('symbol', 'a', 'name', 'Stiffener spacing', 'unit', 'm', 'required', true),
        jsonb_build_object('symbol', 'k', 'name', 'Material factor', 'unit', '', 'required', true, 'default', 1.0),
        jsonb_build_object('symbol', 'nf', 'name', 'Framing factor', 'unit', '', 'required', true, 'default', 1.0),
        jsonb_build_object('symbol', 'tK', 'name', 'Corrosion addition', 'unit', 'mm', 'required', true, 'default', 1.5)
    ),
    'mm',
    'L >= 90m. Evaluates maximum of tS1, tS2, tS3. Simplifies σpℓ to 176.1/k and σpℓmax to 190.8/k. Requires pS1 for tS3.',
    true
);
