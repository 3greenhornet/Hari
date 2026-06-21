-- 002_decision_trace.sql
CREATE TABLE IF NOT EXISTS decision_traces (
    trace_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    turn_number INTEGER NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    model_used TEXT,
    system_prompt_version TEXT,
    temperature REAL,
    user_input TEXT,
    reasoning_chain TEXT,
    generated_response TEXT,
    retrieved_candidate_count INTEGER,
    selected_winner_count INTEGER,
    drives_before JSONB,
    drives_after JSONB,
    perceived_user_intent TEXT,
    intent_confidence REAL,
    thematic_continuity REAL,
    prompt_tokens INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    latency_ms REAL DEFAULT 0,
    error TEXT
);

CREATE TABLE IF NOT EXISTS trace_workspace_items (
    trace_id TEXT NOT NULL REFERENCES decision_traces(trace_id) ON DELETE CASCADE,
    item_id TEXT NOT NULL,
    item_type TEXT,
    source TEXT,
    raw_score REAL,
    final_score REAL,
    attention_weight REAL,
    content_snapshot TEXT,
    is_winner BOOLEAN
);

CREATE INDEX IF NOT EXISTS idx_decision_traces_session ON decision_traces(session_id, turn_number);
CREATE INDEX IF NOT EXISTS idx_trace_workspace_items_trace ON trace_workspace_items(trace_id);