ALTER TABLE hypotheses ADD COLUMN IF NOT EXISTS session_id TEXT;
UPDATE hypotheses SET session_id = 'legacy_global' WHERE session_id IS NULL;
ALTER TABLE hypotheses ALTER COLUMN session_id SET NOT NULL;
CREATE INDEX IF NOT EXISTS idx_hypotheses_session ON hypotheses(session_id);

ALTER TABLE contradictions ADD COLUMN IF NOT EXISTS session_id TEXT;
ALTER TABLE contradictions ADD COLUMN IF NOT EXISTS created_turn INTEGER;
UPDATE contradictions SET session_id = 'legacy_global' WHERE session_id IS NULL;
ALTER TABLE contradictions ALTER COLUMN session_id SET NOT NULL;
CREATE INDEX IF NOT EXISTS idx_contradictions_session ON contradictions(session_id, status);

UPDATE memories SET role = 'participant' WHERE role IN ('user', 'human');
UPDATE memories SET role = 'hari' WHERE role IN ('assistant', 'ai', 'model', 'bot');