-- 036_add_slenderness_plate_formula_rollback.sql

DELETE FROM public.formulas WHERE code = 'PLATE_NET_THICKNESS_SLENDERNESS';
