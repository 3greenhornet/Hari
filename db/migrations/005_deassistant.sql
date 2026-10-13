-- Rename analyst-vocabulary columns and add Sprint 1 telemetry.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='decision_traces' AND column_name='user_input')
       AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='decision_traces' AND column_name='incoming_text') THEN
        ALTER TABLE decision_traces RENAME COLUMN user_input TO incoming_text;
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='decision_traces' AND column_name='perceived_user_intent')
       AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='decision_traces' AND column_name='perceived_intent') THEN
        ALTER TABLE decision_traces RENAME COLUMN perceived_user_intent TO perceived_intent;
    END IF;
END $$;

UPDATE hypotheses SET type = 'person' WHERE type IN ('user', 'other');
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='episodic_memories' AND column_name='speaker') THEN
        UPDATE episodic_memories SET speaker = 'participant' WHERE speaker IN ('user', 'human');
        UPDATE episodic_memories SET speaker = 'hari' WHERE speaker IN ('assistant', 'ai', 'model', 'bot');
    ELSIF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='episodic_memories' AND column_name='role') THEN
        UPDATE episodic_memories SET role = 'participant' WHERE role IN ('user', 'human');
        UPDATE episodic_memories SET role = 'hari' WHERE role IN ('assistant', 'ai', 'model', 'bot');
    END IF;
END $$;

ALTER TABLE decision_traces ADD COLUMN IF NOT EXISTS contamination_hits INTEGER DEFAULT 0;
ALTER TABLE decision_traces ADD COLUMN IF NOT EXISTS expression_mode TEXT;
ALTER TABLE decision_traces ADD COLUMN IF NOT EXISTS thread_survival REAL;
ALTER TABLE decision_traces ADD COLUMN IF NOT EXISTS held BOOLEAN DEFAULT FALSE;
ALTER TABLE decision_traces ADD COLUMN IF NOT EXISTS internal_candidates_count INTEGER DEFAULT 0;
ALTER TABLE decision_traces ADD COLUMN IF NOT EXISTS active_thought_count INTEGER DEFAULT 0;
ALTER TABLE decision_traces ADD COLUMN IF NOT EXISTS feedback_summary JSONB;

CREATE TABLE IF NOT EXISTS cognitive_telemetry (
    id BIGSERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,
    turn_number INTEGER NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    voice_backend TEXT,
    voice_model TEXT,
    fallback_used BOOLEAN DEFAULT FALSE,
    fallback_reason TEXT,
    candidate_count INTEGER,
    candidate_internal_ratio REAL,
    candidate_external_ratio REAL,
    workspace_size INTEGER,
    selected_internal_ratio REAL,
    selected_external_ratio REAL,
    internal_selection_lift REAL,
    workspace_skew REAL,
    winner_type TEXT,
    winner_source TEXT,
    winner_self_reference BOOLEAN,
    thread_resumption_score REAL,
    cognitive_inertia_index REAL,
    active_thought_count INTEGER,
    active_thought_reinforcement INTEGER,
    csi REAL,
    register_markers JSONB,
    response_length INTEGER,
    metadata JSONB
);
CREATE INDEX IF NOT EXISTS idx_cog_telemetry_session ON cognitive_telemetry(session_id, turn_number);
UPDATE curiosity_nodes SET session_id = 'legacy_global' WHERE session_id IS NULL OR session_id = '';
