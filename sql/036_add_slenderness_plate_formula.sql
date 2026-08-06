-- 036_add_slenderness_plate_formula.sql
-- Add net plate thickness slenderness criterion (Sec 3 F.2.2.1).
-- tp >= (b / C) * sqrt(1/k)
-- C = 100 for hull envelope, 125 for other structures; k = material factor.

INSERT INTO public.formulas (code, title, section_no, paragraph_id, page_no, expression, variables, result_unit, notes, verified)
VALUES (
    'PLATE_NET_THICKNESS_SLENDERNESS',
    'Net plate thickness (slenderness criterion)',
    3, 'F.2.2.1', 60,
    '(b / C) * sqrt(1 / k)',
    jsonb_build_array(
        jsonb_build_object('symbol', 'b', 'name', 'Stiffener spacing / plate breadth', 'unit', 'mm', 'required', true),
        jsonb_build_object('symbol', 'C', 'name', 'Slenderness coefficient', 'unit', '', 'required', true, 'default', 100),
        jsonb_build_object('symbol', 'k', 'name', 'Material factor', 'unit', '', 'required', true, 'default', 1.0)
    ),
    'mm',
    'Sec 3 F.2.2.1 net thickness of plate panels. C = 100 for hull envelope, 125 for other structures. k = 1.0 for mild steel.',
    true
)
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
