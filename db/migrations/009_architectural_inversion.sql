ALTER TABLE decision_traces ADD COLUMN IF NOT EXISTS event_present BOOLEAN DEFAULT FALSE;
ALTER TABLE decision_traces ADD COLUMN IF NOT EXISTS event_was_winner BOOLEAN DEFAULT FALSE;
ALTER TABLE decision_traces ADD COLUMN IF NOT EXISTS event_was_supporting BOOLEAN DEFAULT FALSE;
ALTER TABLE decision_traces ADD COLUMN IF NOT EXISTS event_was_ignored BOOLEAN DEFAULT TRUE;
ALTER TABLE decision_traces ADD COLUMN IF NOT EXISTS social_update_applied BOOLEAN DEFAULT FALSE;
ALTER TABLE decision_traces ADD COLUMN IF NOT EXISTS expression_permitted BOOLEAN DEFAULT FALSE;
ALTER TABLE decision_traces ADD COLUMN IF NOT EXISTS expression_reason TEXT;
ALTER TABLE decision_traces ADD COLUMN IF NOT EXISTS winner_origin TEXT;
CREATE INDEX IF NOT EXISTS idx_decision_traces_event_attended
    ON decision_traces (session_id, event_present, event_was_winner);