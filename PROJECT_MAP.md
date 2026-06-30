# Project Map – Hari Core

A flat file tree with a one‑sentence explanation for every file in the repository. Use this to quickly locate where specific functionality lives.

---

## Root Files

| File | Purpose |
|------|---------|
| `README.md` | Project overview, philosophy, quick start, and high-level "what is Hari". |
| `ARCHITECTURE.md` | Deep‑dive: component diagram, cognitive loop, state model, data flow, key design decisions. |
| `AI_CONTEXT.md` | Concise summary for AI assistants – under 500 tokens, covers philosophy, key files, status. |
| `PROJECT_MAP.md` | **This file** – flat file tree with one‑sentence explanations for every file. |
| `AGENTS.md` | AI collaboration guide – non‑negotiable rules for any AI assistant working on this codebase. |
| `CLAUDE.md` | Same as AGENTS.md, with additional notes for Claude (updated 2026‑06‑25). |
| `TODO.md` | Task list and known issues – current priorities, completed items, deferred features. |
| `HARI_COGNITIVE_ECOLOGY.md` | Transformation laws for cognitive objects: memory → pattern → contradiction → curiosity → interest → identity. |
| `run.py` | Entry point for the REPL interface – runs the full TurnPipeline in a terminal session. |
| `app.py` | Entry point for the Streamlit web interface – provides a chat UI with visible cognition. |
| `requirements.txt` | Python dependencies: asyncpg, pgvector, litellm, pydantic, pytest, google-genai. |
| `.env.example` | Template for environment variables: API keys, database URL, feature flags. |

---

## `db/` – Database

| File | Purpose |
|------|---------|
| `connection.py` | Async PostgreSQL connection pool with pgvector registration and table validation. |
| `__init__.py` | Module initializer (empty). |
| `migrations/002_decision_trace.sql` | Schema for `decision_traces` and `trace_workspace_items` tables. |
| `migrations/003_development_ledger.sql` | Schema for `system_interests` and `development_events` tables. |
| `migrations/004_hybrid_retrieval.sql` | Adds `text_search_vector` column, trigger, and GIN index for BM25 keyword search. |

---

## `engine/` – Core Cognitive Engine

| File | Purpose |
|------|---------|
| `__init__.py` | Exports `TurnPipeline`, `generate_lightweight_response`, and `generate_hari_response`. |
| `generate.py` | **Main orchestrator** – `TurnPipeline.execute()` runs the full 14‑step cognitive loop. |
| `attention.py` | Workspace competition – pressure fields, softmax, diversity penalty, 3‑layer fallback. |
| `memory.py` | Memory storage, hybrid retrieval (vector + BM25 + recency + drive boost), embedding generation. |
| `stage1_monologue.py` | Sensory perception – runs LLM to produce `MonologueOutput` (intent, continuity, candidates). |
| `prediction.py` | Prediction error via cosine similarity between last response and current input. |
| `narrative_manager.py` | Persistent narrative threads – create, load active threads, update completion/investment. |
| `curiosity_graph.py` | Persistent curiosity graph – add nodes, update edges, decay importance, sync to DB. |
| `memory_consolidation.py` | Background consolidation – promote high‑significance memories to hypotheses, archive old memories. |
| `consolidation_worker.py` | Background worker – runs consolidation periodically with graceful shutdown. |
| `promotions.py` | **Stub** – central authority for structural creation (pattern, contradiction, interest, identity). |
| `social_cognition.py` | **Stub** – social interpretation (conversation moves, shift analysis, sincerity) – future. |
| `volition_engine.py` | **Stub** – desires, agendas, proactive candidates – future. |
| `client.py` | Gemini client with rate limiting and retries – **deprecated** (use LiteLLM). |
| `development.py` | Stores development events (promotions, interest formation, identity anchors) to the ledger. |
| `health.py` | Health dashboard – single‑pass metrics: turns, workspace empty rate, promotions, interests. |

---

## `models/` – Pydantic Data Models

| File | Purpose |
|------|---------|
| `__init__.py` | Exports all models for convenient importing. |
| `memory_event.py` | `MemoryEvent` – conversation turn with embedding, significance, usage_count, explanatory_power. |
| `monologue_output.py` | `MonologueOutput` – sensory perception output: intent, continuity, dynamic candidates. |
| `decision_trace.py` | `DecisionTrace` and `WorkspaceItemTrace` – full audit trail with winners/losers. |
| `identity.py` | `IdentityModel`, `ConstitutionModel`, `OriginModel`, `SelfModel`, `PerspectiveShift`. |
| `relational.py` | `RelationshipModel`, `Interest`, `Contradiction`, `RelationalLandmark` – per‑user and cognitive tension. |
| `narrative.py` | `NarrativeThread` – persistent narrative with completion estimate and emotional investment. |
| `curiosity_node.py` | `CuriosityNode` – open question in the curiosity graph. |
| `hypothesis.py` | `Hypothesis` – belief about user, self, or world with confidence and evidence links. |
| `development.py` | `DevelopmentEvent` – permanent cognitive landmarks (identity mutation, paradigm shift). |
| `development_event.py` | `DevelopmentEvent` – event‑sourced changes with source attribution and metadata. |
| `interaction.py` | `InteractionModel` – social interpretation output (conversation move, shift analysis) – future. |
| `thought.py` | `Thought` – incomplete processing loops with execution pressure. |
| `volition.py` | `Desire`, `Agenda`, `ActiveProject` – volition data models (future). |
| `workspace.py` | Alias for `WorkspaceItem` (imported from `engine.attention`). |

---

## `psyche/` – State System

| File | Purpose |
|------|---------|
| `__init__.py` | Module initializer (empty). |
| `state.py` | `HariState` – four‑layer state: drives (0‑1), VAD (-1‑1), conversational, meta‑cognitive. |
| `cascades.py` | Deterministic state updates: fatigue, sovereignty, coherence, completion, session horizon. |
| `grace.py` | `GraceTracker` – rolling engagement window, modulates negative deltas based on user engagement. |
| `fallback_emotions.py` | **Stub** – deterministic VAD formulas for when LLM deltas are missing (future). |

---

## `providers/` – LLM Abstraction

| File | Purpose |
|------|---------|
| `base.py` | `BaseProvider` abstract class – defines `generate_structured()` and `generate_text()`. |
| `gemini.py` | `GeminiProvider` – concrete implementation using Google Gemini with JSON schema support. |
| `factory.py` | `get_provider()` – singleton factory for provider instances. |

---

## `scripts/` – Migrations and Setup

| File | Purpose |
|------|---------|
| `init_db.sql` | Initial database schema: memories, archived_memories, hypotheses, episodic_memories, etc. |
| `migrate_all.py` | Migration runner – creates all tables, adds columns, indexes, and triggers. |
| `reset_db.ps1` | PowerShell script to reset the database (drops and recreates memories table). |

---

## `tests/` – Unit Tests and Evaluation

| File | Purpose |
|------|---------|
| `conftest.py` | Pytest fixtures – event loop and mocked Gemini client for testing. |
| `test_state.py` | Unit tests for `HariState` – asymptotic updates, natural drift, velocity. |
| `test_behavior.py` | Behavioural tests (mocked) – checks pipeline doesn't crash, verifies basic response generation. |
| `evaluator.py` | G‑Eval qualitative and quantitative evaluation framework – rubrics, self‑consistency, metrics. |

---

## `utils/` – Helpers

| File | Purpose |
|------|---------|
| `async_input.py` | `ainput()` – async wrapper for Python's `input()`, used in `run.py`. |
| `logger.py` | Structured JSON logging – session logs, `log_event()`, `harilog` decorator. |

---

## Summary

| Directory | File Count | Purpose |
|-----------|------------|---------|
| Root | 10+ | Project entry, docs, configuration |
| `db/` | 5 | Database connection and migrations |
| `engine/` | 15 | Core cognitive engine |
| `models/` | 14 | Pydantic data models |
| `psyche/` | 4 | State system |
| `providers/` | 3 | LLM abstraction |
| `scripts/` | 3 | Setup and migrations |
| `tests/` | 4 | Unit tests and evaluation |
| `utils/` | 2 | Helpers |

---

> *Use this map to navigate the codebase. Each file has a single, clear responsibility.*