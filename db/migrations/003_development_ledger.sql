-- 003_development_ledger.sql

-- 1. Normalized interests table (prevents name drift)
CREATE TABLE IF NOT EXISTS system_interests (
    interest_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    interest_name TEXT NOT NULL,
    current_strength FLOAT NOT NULL DEFAULT 0.0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_interest_strength CHECK (current_strength >= 0.0 AND current_strength <= 1.0)
);

CREATE INDEX IF NOT EXISTS idx_interests_session ON system_interests(session_id);

-- 2. Development Events Ledger
CREATE TABLE IF NOT EXISTS development_events (
    sequence_number BIGINT GENERATED ALWAYS AS IDENTITY,
    event_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    turn_number INTEGER NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,

    event_type TEXT NOT NULL,

    -- Structured attribution (JSONB for flexibility)
    source_attribution JSONB NOT NULL DEFAULT '[]'::jsonb,
    confidence FLOAT NOT NULL DEFAULT 0.0,
    reason TEXT NOT NULL,

    -- Foreign key to normalized interests table
    interest_id TEXT REFERENCES system_interests(interest_id) ON DELETE SET NULL,
    old_strength FLOAT CHECK (old_strength IS NULL OR (old_strength >= 0.0 AND old_strength <= 1.0)),
    new_strength FLOAT CHECK (new_strength IS NULL OR (new_strength >= 0.0 AND new_strength <= 1.0)),

    narrative_id TEXT,
    narrative_title TEXT,

    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_development_event_type CHECK (event_type IN (
        'promotion_attempt', 'promotion_success', 'promotion_decay',
        'interest_formed', 'interest_strengthened', 'interest_weakened',
        'identity_anchor_formed', 'narrative_created', 'narrative_archived'
    ))
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_dev_events_timeline ON development_events(session_id, turn_number, sequence_number ASC);
CREATE INDEX IF NOT EXISTS idx_dev_events_interest ON development_events(interest_id, sequence_number DESC) WHERE interest_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_dev_events_source_jsonb ON development_events USING gin (source_attribution);