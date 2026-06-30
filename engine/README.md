# Engine Module – Hari Cognitive Engine

This module contains the **core cognitive engine** – all logic for prediction, memory, attention, interpretation, dialogue, and consolidation. It is the heart of Hari.

---

## Overview
engine/
├── init.py # Exports TurnPipeline, generate_lightweight_response, generate_hari_response
├── generate.py # Main orchestrator – TurnPipeline
├── attention.py # Workspace competition
├── memory.py # Memory storage and retrieval
├── stage1_monologue.py # Sensory perception
├── prediction.py # Prediction error
├── narrative_manager.py # Persistent narratives
├── curiosity_graph.py # Persistent curiosity graph
├── memory_consolidation.py # Background consolidation
├── consolidation_worker.py # Background worker
├── promotions.py # Stub – central authority for structural creation
├── social_cognition.py # Stub – social interpretation (future)
├── volition_engine.py # Stub – desires and agendas (future)
├── client.py # Gemini client (deprecated; use LiteLLM)
├── development.py # Development event storage
└── health.py # Health dashboard

text

---

## Core Files

### `generate.py` – TurnPipeline (Orchestrator)

The main orchestrator. `TurnPipeline.execute()` runs the full 14‑step cognitive loop:

1. Compute prediction error
2. Retrieve memory candidates
3. Run monologue (interpretation)
4. Allocate workspace (attention)
5. Broadcast feedback (state update)
6. Increment memory usage
7. Store DecisionTrace (audit)
8. Generate dialogue
9. Store assistant memory
10. Natural drift
11. Wire curiosity trigger → graph
12. Wire narrative thread creation
13. Consolidation (background)

**Entry point:**
```python
pipeline = TurnPipeline(session_id, state, grace_tracker)
result = await pipeline.execute(user_input, turn_count, trace_id)
attention.py – Workspace Competition
Implements Global Workspace Theory. Items compete via pressure fields + softmax.

Key functions:

load_workspace() – main competition

load_workspace_secured() – 3‑layer fallback (hybrid → episodic → inertia)

compute_total_salience() – weighted blend of pressures

broadcast_feedback() – state updates from workspace composition

apply_workspace_diversity_penalty() – MMR‑style thematic diversity

Workspace size: 5–7 slots.

Pressure fields:

Relevance (cosine similarity)

Novelty (prediction error)

Curiosity (state + item type boost)

Completion (state + open thread urgency)

Future: Exploratory Potential, Shared Significance, Coherence Tension

memory.py – Memory System
Hybrid retrieval: vector (cosine) + BM25 (keyword) + recency + drive boost.

Key functions:

retrieve_candidates_hybrid() – main retrieval with multi‑factor scoring

retrieve_similar() – pure cosine similarity (legacy)

store_memory() – add‑only storage with embedding and significance

increment_memory_usage() – usage count + significance boost (+0.005)

embed() – generates embeddings via Gemini

Retrieval formula:

text
score = (vector_similarity × 0.5) + (keyword_score × 0.3) + (recency_score × 0.2)
With drive boosts: curiosity +0.15 for unused memories, completion +0.20 for open threads.

stage1_monologue.py – Sensory Perception
LLM interprets user input. Outputs observations – no command flags.

Key function:

run_monologue() – returns MonologueOutput

Outputs:

perceived_user_intent (curious, avoiding, testing, help_seeking, sharing, derailing)

intent_confidence (0.0–1.0)

thematic_continuity (0.0–1.0)

user_engagement_estimate (0.0–1.0)

dynamic_candidates – conversational actions Hari can perform

curiosity_trigger – new question

hypothesis_update – new insight

self_belief_update – new self‑understanding

memory_significance (0.0–1.0)

Uses LiteLLM fallback chain: Gemini → Groq → Mistral → OpenRouter.

prediction.py – Prediction Error
Deterministic surprise calculation.

Key function:

compute_prediction_error() – cosine similarity between last response and current input

Formula:

text
surprise = 1 - cosine_similarity(embed(last_response), embed(current_input))
Returns 0.0 (no surprise) to 1.0 (complete surprise).

narrative_manager.py – Narrative Threads
Persistent narratives across turns.

Key functions:

create_thread() – new narrative thread

load_active_threads() – active threads for workspace

update_thread() – update completion, investment, status

flush_updates() – batch database updates

Fields: title, description, status, completion_estimate (0–1), emotional_investment (0–1).

curiosity_graph.py – Curiosity Graph
Persistent graph of open questions.

Key functions:

add_node() – add or update a curiosity node with session isolation and traceability

update_edge() – strengthen connection between two nodes

get_top_nodes() – top nodes by importance

decay() – decay importance over time

observe_coactivation() – automatically connect nodes that co‑occur in workspace (future)

Storage: PostgreSQL with networkx for in‑memory graph operations, batched sync to DB.

memory_consolidation.py – Consolidation
Background processing: hypothesis promotion, memory archival.

Key functions:

run_consolidation() – full consolidation cycle

promote_to_hypothesis() – high‑significance memory → hypothesis (LiteLLM)

archive_old_memories() – compress and archive old memories

store_hypothesis() – persist hypothesis to DB

Promotion threshold: SIGNIFICANCE_PROMOTION_THRESHOLD (default 0.75).

consolidation_worker.py – Background Worker
Runs consolidation periodically.

Key functions:

ConsolidationManager.start() – start background loop

ConsolidationManager.stop() – graceful shutdown

Interval: 10 turns or 60 seconds.

promotions.py – Stub
Central authority for structural creation. Currently bypassed – will be implemented in Sprint 3.

Stubbed functions:

promote_memory_to_pattern()

promote_contradiction_to_curiosity()

promote_curiosity_to_interest()

record_perspective_shift()

promote_to_development_event()

archive_inactive_structures()

social_cognition.py – Stub
Social interpretation (future). Will detect conversation moves, topic shifts, sincerity, relationship impact.

Stubbed function:

interpret_turn() – returns InteractionModel

volition_engine.py – Stub
Desires, agendas, and proactive candidates (future).

Stubbed class:

VolitionEngine – manages desires, agendas, projects; get_proactive_candidates() returns workspace candidates.

client.py – Gemini Client (Deprecated)
Rate limiting and retries for Gemini. Deprecated – use LiteLLM fallback in stage1_monologue.py and generate.py.

development.py – Development Event Storage
Stores development events (promotions, interest formation, identity anchors) to the development_events table.

Key function:

store_development_event() – persists a DevelopmentEvent

health.py – Health Dashboard
Single‑pass health metrics.

Metrics:

turns – total turns

workspace_empty_rate – percentage of empty workspace

promotion_attempts / promotion_successes

active_interests – current interests

identity_anchors – stable identity anchors

status – "healthy" if empty_rate < 1%

Dependencies
psyche/ – state system (HariState, GraceTracker, cascades)

models/ – data models (MemoryEvent, MonologueOutput, DecisionTrace, etc.)

db/ – database connection (get_pool)

providers/ – LLM abstraction (BaseProvider, GeminiProvider) – though currently LiteLLM is used directly

litellm – LLM fallback chain

Testing
bash
pytest tests/test_engine.py
Next Steps (Wiring Missing)
File	Missing Functionality	Ticket
generate.py	Persist self_belief_update	004
generate.py	Persist hypothesis_update	005
curiosity_graph.py	Call update_edge() (curiosity edges)	006
generate.py	Wire IdentityModel into system prompt	008
generate.py	Refactor _build_conversational_context()	007
The engine is where Hari's cognition happens. Each file has a single, clear responsibility. Modifications must preserve the architectural principles – workspace as sole gateway, no hardcoded heuristics, observability first.