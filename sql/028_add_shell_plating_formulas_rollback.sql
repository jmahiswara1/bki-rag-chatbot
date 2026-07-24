-- Rollback for Migration 028: Remove Shell Plating Formulas
DELETE FROM public.formulas 
WHERE code IN (
    'BOTTOM_PLATING_L_LESS_90',
    'BOTTOM_PLATING_L_GREATER_90',
    'SIDE_PLATING_L_LESS_90',
    'SIDE_PLATING_L_GREATER_90'
);
