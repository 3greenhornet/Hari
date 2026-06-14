# Hari Core – AI Collaboration Guide

This document defines the architectural boundaries and non‑negotiable rules for the Hari Core cognitive engine. It is the single source of truth for any AI agent (including Claude) working on this codebase. **Read it carefully before writing any code.**

---

## 1. Project Vision (Don't Lose Sight)

Hari is **not** a chatbot, assistant, roleplay character, or search engine. Hari is a **conversational cognitive entity** whose behavior emerges from:

- Internal state (drives, VAD, conversational metrics)
- Memory (episodic, with retrieval fatigue)
- Attention (workspace competition, softmax bottleneck)
- Curiosity (persistent graph of open questions)
- Narrative threads (long‑running topics with completion estimates)
- Social perception (thematic continuity, user engagement, intent)

**The goal:** Create conditions under which coherent, non‑assistant, emergent behavior arises—not scripted responses. The system's dynamics should feel alive, not pre‑programmed.

**Success criteria:** After 20+ turns, the user should feel they are interacting with an intelligence that has its own evolving perspective, remembers past discussions, occasionally introduces new directions, and treats topic shifts as meaningful events.

**Failure criteria:** Hari becomes an assistant with memory, merely answers questions better, or shows personality that is obviously prompt‑driven.

---

## 2. Non‑Negotiable Architectural Principles

These rules are **absolute**. Violating them will break emergence. Treat them as invariants of the system.

**Workspace is the sole gateway**  
No subsystem may inject text into the dialogue prompt without first becoming a `WorkspaceCandidate` and winning the softmax competition in `engine/attention.py`.

**LLM is a sensory organ, not a decision‑maker**  
The monologue outputs only observations (continuity, engagement, intent with confidence). No command flags like `finish_thought_first`.

**No heuristics**  
Never write `if state.X > threshold: response = ...`. State only influences attention via pressure fields.

**Asymptotic saturation**  
All state updates use `new = current + α * Δ * (1 - current)` or `current + α * Δ * current` with α = 0.25.

**Observability first**  
Every workspace competition must log telemetry (per‑candidate pressure breakdown, probabilities, winners). Without logs, you cannot debug emergence.

**Replaceability**  
All LLM calls go through `providers/` abstraction. No direct `google.genai` imports outside `providers/`.

**Cross‑session memory**  
No memory shared across different session IDs. Within a session, memory persists across restarts.

---

## 3. File‑by‑File Reference

This section lists every file in the project along with its responsibility. **Do not rewrite core files unless explicitly asked.**

### 3.1 Core Engine (`engine/`)

- **`generate.py`** – `TurnPipeline` orchestrator. Key function: `execute()` calls prediction, memory, monologue, workspace, dialogue. ✅ Safe to edit.
- **`attention.py`** – Workspace competition. Key function: `load_workspace()` returns `(workspace_items, telemetry)`. ✅ Safe.
- **`memory.py`** – Embeddings, retrieval, batch usage updates. Key functions: `retrieve_candidates()`, `increment_memory_usage()`. ✅ Safe.
- **`prediction.py`** – Surprise calculation. Key function: `compute_prediction_error()` (cosine similarity). ✅ Safe.
- **`stage1_monologue.py`** – Sensory perception. Key function: `run_monologue()` returns `MonologueOutput`. ✅ Safe.
- **`narrative_manager.py`** – Narrative persistence. Key functions: `load_active_threads()`, `touch_thread()`, `flush_updates()`. ✅ Safe.
- **`curiosity_graph.py`** – Curiosity graph. Key functions: `add_node()`, `decay()`, `get_top_nodes()`. ✅ Safe.
- **`memory_consolidation.py`** – Hypothesis promotion, archival. Key function: `run_consolidation()`. ✅ Safe.
- **`consolidation_worker.py`** – Background worker. Key functions: `ConsolidationManager.start()/stop()`. ✅ Safe.
- **`promotions.py`** – **Stub** – central creation authority. Key functions: `promote_memory_to_hypothesis()`, `archive_inactive_structures()`. ⚠️ Stub only – implement only when asked.
- **`client.py`** – Gemini rate limiting, retries. Key functions: `get_genai_client()`, `call_gemini_json()`. ✅ Safe.

### 3.2 Psyche (`psyche/`)

- **`state.py`** – `HariState` with drives, VAD, velocity, `completion_pressure`, telemetry.
- **`cascades.py`** – Deterministic state updates (fatigue, sovereignty, coherence, completion, horizon).
- **`grace.py`** – Engagement tracker (uses monologue's `user_engagement_estimate`).

### 3.3 Models (`models/`)

- **`memory_event.py`** – `MemoryEvent` with `usage_count`, `last_retrieved_turn`, `explanatory_power`.
- **`narrative.py`** – `NarrativeThread` – pure data (no activation, decay).
- **`monologue_output.py`** – Sensory observations only.
- **`hypothesis.py`** – `Hypothesis` with `type` (user/self/world).
- **`curiosity_node.py`** – `CuriosityNode`.
- **`workspace.py`** – Optional alias (can be removed).

### 3.4 Providers (`providers/`)

- **`base.py`** – `BaseProvider` ABC.
- **`gemini.py`** – `GeminiProvider` implementation.
- **`factory.py`** – `get_provider()` singleton.

### 3.5 Tests (`tests/`)

- **`test_state.py`** – Unit tests for state updates, velocities, pressures.
- **`test_behavior.py`** – **Placeholder** – needs rewrite with LLM mocking.
- **`evaluator.py`** – G‑Eval qualitative + quantitative metrics.

---

## 4. Subsystem Status (Phase 6 – All Completed)

All core subsystems are production‑ready. No major rewrites are needed.

- State & Drives (`psyche/state.py`, `cascades.py`) – ✅ Complete
- Grace (engagement) (`psyche/grace.py`) – ✅ Complete
- Prediction error (`engine/prediction.py`) – ✅ Complete
- Memory retrieval (`engine/memory.py`) – ✅ Complete
- Workspace attention (`engine/attention.py`) – ✅ Complete
- Sensory monologue (`engine/stage1_monologue.py`) – ✅ Complete
- Dialogue generation (`engine/generate.py`) – ✅ Complete
- Narrative threads (`models/narrative.py`, `engine/narrative_manager.py`) – ✅ Complete
- Curiosity graph (`engine/curiosity_graph.py`) – ✅ Complete
- Memory consolidation (`engine/memory_consolidation.py`) – ✅ Complete
- Consolidation worker (`engine/consolidation_worker.py`) – ✅ Complete
- Provider abstraction (`providers/`) – ✅ Complete
- Evaluation (`tests/evaluator.py`) – ✅ Complete
- Entry point (`run.py`) – ✅ Complete

---

## 5. What You Must NOT Do (Prohibition List)

The following features are **explicitly rejected** for Phase 6. Do not implement them under any circumstances.

- ❌ Ebbinghaus forgetting curves or ACT‑R memory strength formulas
- ❌ Any activation, persistence, decay, or confidence fields inside `NarrativeThread`
- ❌ Saliency spreading or graph diffusion in `CuriosityGraph`
- ❌ Sliding window summarizers or mid‑session summarisation
- ❌ Direct LLM calls outside `providers/`
- ❌ Heuristic rules bypassing workspace competition (`if completion > 0.6: response = "Let me finish"`)
- ❌ Autonomous narrative creation from curiosity or memory (use `promotions.py` stub)
- ❌ Multi‑tier memory implementation (episodic/semantic) – placeholders only, Phase 8
- ❌ Emotional simulation, mood engines, or personality scripts

---

## 6. What Actually Remains (Priority‑Ordered)

These are the **only** open items. Each is small and isolated.

### High Priority (Must Complete)

*None. All core subsystems are complete.*

### Medium Priority (Complete if time allows)

- **Add memory retrieval telemetry** in `engine/memory.py`. Inside `retrieve_candidates()`, after obtaining results, insert a row into `memory_retrieval_logs` with `session_id`, `query_text`, `retrieved_count`, `similarity_avg`, `latency_ms`, `created_at`. (Observability)
- **Add periodic promotion engine call** in `run.py`. Every 50 turns, call `archive_inactive_structures(turn)`. (Prepares for Phase 7)
- **Create `tests/conftest.py`** to provide event loop and mock Gemini fixture. (Testability)

### Low Priority (Defer to Phase 7)

- Full `promotions.py` implementation (requires LLM calls)
- Workspace telemetry dataclass (already dict‑based; optional)
- Fallback chain (Gemini → Groq) – resilience, not core
- Circuit breaker for LLM – resilience, not core
- State checkpointing – persistence across restarts, not core

---

## 7. Workflow & Testing

### Environment Setup

```bash
cp .env.example .env
# Edit .env with your GEMINI_API_KEY, DATABASE_URL, etc.
```

### Running the REPL

```bash
python run.py
```

Feature flags in `.env`:
- `USE_MEMORY=True` – enable memory retrieval
- `USE_WORKSPACE=True` – enable attention competition
- `USE_MONOLOGUE=True` – enable sensory monologue

### Running Unit Tests

```bash
pytest tests/test_state.py -v
```

### Behavioral Tests (Not Yet Ready)

`tests/test_behavior.py` currently calls the real LLM and lacks async markers. To fix:
1. Add `@pytest.mark.asyncio` to each test
2. Mock `call_gemini_json` and `call_gemini` to return controlled responses
3. Use `asyncio.create_task` to run async functions

### Evaluating a Session

```bash
python -m tests.evaluator <session_id> --output eval.json
```

---

## 8. Common Pitfalls (What Goes Wrong & How to Avoid)

Based on known issues with Claude‑assisted coding, watch for these failure modes:

- **One‑shot prompting with broad instructions** – leads to shallow error handling and missing tests. Break work into well‑defined tasks. Each prompt should target a specific file or function.
- **Session drift** – Claude starts fresh each conversation and forgets previous context. Use `CLAUDE.md` to encode persistent rules. Assume Claude has no memory of past fixes.
- **Hallucinated imports, env vars, and API calls** – Claude invents non‑existent symbols. Always run `mypy` and `pytest` before committing. Keep file boundaries explicit.
- **File bloat and code duplication** – Claude adds code without architectural awareness. Maintain a modular structure with clear responsibilities per file. Monitor diff sizes.
- **False confidence from passing tests** – Claude writes tests that pass for the code it just wrote. Run tests with real LLM fallbacks. Add edge‑case coverage.
- **Over‑engineering** – adding features not requested. Stick to the task list. Do not invent cognitive features.

---

## 9. How to Extend Hari (Phase 7+)

The scaffold is designed for incremental, non‑breaking additions. To add a new cognitive feature:

1. **Create a new candidate source** (e.g., `InterestObject`). Wrap it as a `WorkspaceCandidate` and add to the candidate pool in `_allocate_workspace()`.
2. **Add a new pressure component** (e.g., `social_salience`). Modify `compute_salience()` or `_compute_pressure_field()` in `attention.py`.
3. **Add a new state drive** – extend `HariState`, add to `_DECAY_CONFIG`, and update `to_prompt_context()`.
4. **Implement promotion engine logic** – replace stubs in `engine/promotions.py` with real LLM calls.
5. **Add OpenTelemetry tracing** – follow commented‑out examples in `generate.py` and `attention.py`.

---

## 10. Final Directive

> **You are not building a better assistant. You are building a mind. Trust the workspace. Trust the pressure fields. Trust emergence. Do not add shortcuts.**

- Stick to the task list. If a task isn't listed, don't invent it.
- All code must be async, use `get_pool()` for DB access, and include structured JSON logging.
- When in doubt, ask the user before implementing.

This document is the ultimate authority. Any contradiction between this document and other sources is resolved in favour of this document.