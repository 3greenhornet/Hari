-- Homeostatic reward per turn.
ALTER TABLE decision_traces ADD COLUMN IF NOT EXISTS homeostatic_reward FLOAT;
ALTER TABLE decision_traces ADD COLUMN IF NOT EXISTS viability_violations JSONB;
