-- Reflection edits and workspace observability.
ALTER TABLE decision_traces ADD COLUMN IF NOT EXISTS reflection_edits_applied JSONB;
ALTER TABLE decision_traces ADD COLUMN IF NOT EXISTS focus_stability_ratio FLOAT;
ALTER TABLE decision_traces ADD COLUMN IF NOT EXISTS winner_origin TEXT;
ALTER TABLE decision_traces ADD COLUMN IF NOT EXISTS pursuit_registry_snapshot JSONB;
