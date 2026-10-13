-- Persistent pursuit registry.
CREATE TABLE IF NOT EXISTS pursuits (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    content TEXT NOT NULL,
    source TEXT NOT NULL,
    created_turn INTEGER NOT NULL,
    last_reinforced_turn INTEGER NOT NULL,
    strength FLOAT NOT NULL DEFAULT 0.5,
    reinforcement_history INTEGER[] DEFAULT '{}',
    origin_signature TEXT NOT NULL,
    target_source_id TEXT,
    target_item_type TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_pursuits_session_active ON pursuits(session_id, is_active, strength DESC);
CREATE INDEX IF NOT EXISTS idx_pursuits_last_reinforced ON pursuits(session_id, last_reinforced_turn DESC);
