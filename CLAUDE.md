# Hari Core – AI Collaboration Guide (Updated 2026-06-25)

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

**No hardcoded heuristics**  
Never write `if state.X > threshold: response = ...`. State only influences attention via pressure fields. This includes:
- ❌ No `if len(user) < 10: state.update(...)`
- ❌ No `if topic_shift > threshold: question_user()`
- ❌ No direct drive-to-response mappings

**Asymptotic saturation**  
All state updates use `new = current + α * Δ * (1 - current)` or `current + α * Δ * current` with α = 0.25.

**Observability first**  
Every workspace competition must log telemetry (per‑candidate pressure breakdown, probabilities, winners). Without logs, you cannot debug emergence.

**Replaceability**  
All LLM calls go through `providers/` abstraction. No direct `google.genai` imports outside `providers/`.

**Cross‑session memory**  
No memory shared across different session IDs. Within a session, memory persists across restarts.

**No prompt leakage**  
The dialogue model must never see raw state variables, workspace weights, or implementation details. Only interpreted state (e.g., "slightly curious") should be exposed.

---

## 3. File‑by‑File Reference

This section lists every file in the project along with its responsibility. **Do not rewrite core files unless explicitly asked.**

### 3.1 Core Engine (`engine/`)

- **`generate.py`** – `TurnPipeline` orchestrator. Key function: `execute()` calls prediction, memory, monologue, workspace, dialogue. ✅ Safe to edit.
- **`attention.py`** – Workspace competition. Key functions: `load_workspace()`, `load_workspace_secured()`, `apply_workspace_diversity_penalty()`. ✅ Safe.
- **`memory.py`** – Embeddings, hybrid retrieval (vector + BM25 + recency + drive boost), batch usage updates. Key functions: `retrieve_candidates_hybrid()`, `increment_memory_usage()`. ✅ Safe.
- **`prediction.py`** – Surprise calculation. Key function: `compute_prediction_error()` (cosine similarity). ✅ Safe.
- **`stage1_monologue.py`** – Sensory perception. Key function: `run_monologue()` returns `MonologueOutput`. ✅ Safe (Groq fallback active).
- **`narrative_manager.py`** – Narrative persistence. Key functions: `load_active_threads()`, `create_thread()`, `update_thread()`. ✅ Safe.
- **`curiosity_graph.py`** – Curiosity graph. Key functions: `add_node()`, `decay()`, `get_top_nodes()`. **Now wired** – session isolation and traceability active.
- **`memory_consolidation.py`** – Hypothesis promotion, archival. Key function: `run_consolidation()`. ✅ Safe (LiteLLM cascade).
- **`consolidation_worker.py`** – Background worker. Key functions: `ConsolidationManager.start()/stop()`. ✅ Safe.
- **`promotions.py`** – **Stub** – central creation authority. ⚠️ Currently bypassed for testing; direct wiring used for curiosity, narrative, and significance.
- **`dispatcher.py`** – **Future** – cognitive side‑effect dispatcher (deferred, not yet implemented).
- **`health.py`** – Health dashboard. Single‑pass metrics for workspace_empty_rate, active_interests, etc. ✅ Safe.
- **`development.py`** – DevelopmentLedger storage. ✅ Safe.

### 3.2 Psyche (`psyche/`)

- **`state.py`** – `HariState` with drives, VAD, velocity, `completion_pressure`, telemetry.
- **`cascades.py`** – Deterministic state updates (fatigue, sovereignty, coherence, completion, horizon).
- **`grace.py`** – Engagement tracker (uses monologue's `user_engagement_estimate`).

### 3.3 Models (`models/`)

- **`memory_event.py`** – `MemoryEvent` with `usage_count`, `last_retrieved_turn`, `explanatory_power`, `computed_score`.
- **`narrative.py`** – `NarrativeThread` – pure data (no activation, decay).
- **`monologue_output.py`** – Sensory observations only.
- **`hypothesis.py`** – `Hypothesis` with `type` (user/self/world).
- **`curiosity_node.py`** – `CuriosityNode`.
- **`decision_trace.py`** – Full audit trail with winners/losers.
- **`development_event.py`** – Event‑sourcing for promotions and identity formation.
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

## 4. Subsystem Status (Phase C – Complete)

All core subsystems are now operational. No major rewrites are needed.

| System | Status | Notes |
| :--- | :--- | :--- |
| State & Drives | ✅ Complete | Asymptotic updates, cascades, natural drift |
| Grace (engagement) | ✅ Complete | Rolling engagement tracker |
| Prediction error | ✅ Complete | Cosine similarity |
| Memory retrieval | ✅ Complete | Hybrid retrieval (vector + BM25 + recency + drive boost) |
| Workspace attention | ✅ Complete | Pressure fields, softmax, diversity penalty, 3‑layer fallback |
| Sensory monologue | ✅ Complete | Groq fallback (Gemini 429 resolved) |
| Dialogue generation | ✅ Complete | LiteLLM fallback chain |
| Narrative threads | ✅ Complete | Creation, persistence, timezone‑safe |
| Curiosity graph | ✅ Complete | Wired, session isolation, traceability (84 nodes) |
| Memory consolidation | ✅ Complete | LiteLLM cascade, 5 hypotheses created |
| Consolidation worker | ✅ Complete | Background processing |
| DecisionTrace | ✅ Complete | Full audit trail (84 traces, 409 items) |
| Health Dashboard | ✅ Complete | Single‑pass metrics |
| Memory significance | ✅ Complete | Wired and varying (0.4–0.92) |
| Retrieval reinforcement | ✅ Complete | `significance += 0.005` per retrieval |
| Dynamic candidates | ✅ Complete | Top‑2 injected; occasionally wins workspace |

---

## 5. What You Must NOT Do (Prohibition List – Expanded)

The following features are **explicitly rejected** for the current phase. Do not implement them under any circumstances.

- ❌ Ebbinghaus forgetting curves or ACT‑R memory strength formulas
- ❌ Any activation, persistence, decay, or confidence fields inside `NarrativeThread`
- ❌ Saliency spreading or graph diffusion in `CuriosityGraph`
- ❌ Sliding window summarizers or mid‑session summarisation
- ❌ Direct LLM calls outside `providers/`
- ❌ Heuristic rules bypassing workspace competition (`if completion > 0.6: response = "Let me finish"`)
- ❌ Autonomous narrative creation from curiosity or memory (use `promotions.py` stub)
- ❌ Multi‑tier memory implementation (episodic/semantic) – placeholders only, Phase 8
- ❌ Emotional simulation, mood engines, or personality scripts
- ❌ **Prompt leakage** – exposing raw state variables, drive values, or workspace weights to the dialogue model
- ❌ **Naïve datetime handling** – all timestamps must be timezone‑aware (`datetime.now(timezone.utc)`)
- ❌ **Direct injection** of dynamic candidates without workspace competition

---

## 6. What Actually Remains (Priority‑Ordered)

### Immediate Priorities (Current Sprint)

- [ ] **Curiosity edges** – `update_edge()` exists but never called; nodes remain isolated
- [ ] **Self‑belief persistence** – monologue outputs `self_belief_update`, but it is never stored
- [ ] **Hypothesis update persistence** – monologue outputs `hypothesis_update`, not stored (distinct from promotion‑created hypotheses)
- [ ] **Initiative boost for dynamic candidates** – when user explicitly asks for a new topic, boost their salience
- [ ] **Prompt refinement** – further reduce mirroring and over‑analysis

### Medium Priority (Next Sprint)

- [ ] **`broadcast_feedback` strengthening** – increase coefficients so drives move more meaningfully
- [ ] **Social cognition** – intent/tone detection, relationship tracking (Phase D)
- [ ] **Identity anchors** – stable interests → identity (Phase D)

### Low Priority (Deferred to Future Phases)

- [ ] **Metacognition** – self‑assessment, confidence tracking (Phase F)
- [ ] **System 3 / Persistent Agent** (Phase G)
- [ ] **Persona Vectors / Activation Steering** – requires open‑weight models
- [ ] **Fine‑Tuning** – no dataset, no compute
- [ ] **Neuro‑Symbolic Self‑Modification** – far future
- [ ] **Volition Engine** – self‑generated goals (Phase E)
- [ ] **World Models** – need stable memory and promotions first

---

## 7. Success Metrics (Current vs Target)

| Metric | Current | Target | Status |
| :--- | :--- | :--- | :--- |
| Curiosity nodes | 86 | > 50 | ✅ |
| Narrative threads | Created in sessions | > 3 | ✅ |
| Hypotheses | 5 in DB | > 3 | ✅ |
| Memory significance variation | 0.4–0.92 | Spread > 0.2 | ✅ |
| Workspace empty rate | < 1% | < 5% | ✅ |
| Spontaneous topic initiation | ~1 per 8‑10 turns | ≥ 1 per 5 | ⚠️ Improving |

---

## 8. Workflow & Testing

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

## 9. Common Pitfalls (What Goes Wrong & How to Avoid)

Based on known issues with Claude‑assisted coding and our own experience, watch for these failure modes:

- **One‑shot prompting with broad instructions** – leads to shallow error handling and missing tests. Break work into well‑defined tasks.
- **Session drift** – Claude starts fresh each conversation and forgets previous context. Use `CLAUDE.md` to encode persistent rules.
- **Hallucinated imports, env vars, and API calls** – Always run `mypy` and `pytest` before committing. Keep file boundaries explicit.
- **File bloat and code duplication** – Maintain modular structure with clear responsibilities per file.
- **False confidence from passing tests** – Run tests with real LLM fallbacks. Add edge‑case coverage.
- **Over‑engineering** – adding features not requested. Stick to the task list.
- **Prompt leakage** – The dialogue model should never see raw state, drives, or workspace weights. Use interpreted summaries.
- **Naïve datetime handling** – All timestamps must be timezone‑aware (`datetime.now(timezone.utc)`).
- **Ignoring monologue outputs** – The monologue generates rich signals; ensure they are wired to persistent storage.

---

## 10. How to Extend Hari (Phase 7+)

The scaffold is designed for incremental, non‑breaking additions. To add a new cognitive feature:

1. **Create a new candidate source** (e.g., `InterestObject`). Wrap it as a `WorkspaceCandidate` and add to the candidate pool in `_allocate_workspace()`.
2. **Add a new pressure component** (e.g., `social_salience`). Modify `compute_salience()` or `_compute_pressure_field()` in `attention.py`.
3. **Add a new state drive** – extend `HariState`, add to `_DECAY_CONFIG`, and update `to_prompt_context()`.
4. **Implement promotion engine logic** – replace stubs in `engine/promotions.py` with real LLM calls.
5. **Add OpenTelemetry tracing** – follow commented‑out examples in `generate.py` and `attention.py`.

---

## 11. Final Directive

> **You are not building a better assistant. You are building a mind. Trust the workspace. Trust the pressure fields. Trust emergence. Do not add shortcuts.**

- Stick to the task list. If a task isn't listed, don't invent it.
- All code must be async, use `get_pool()` for DB access, and include structured JSON logging.
- When in doubt, ask the user before implementing.

This document is the ultimate authority. Any contradiction between this document and other sources is resolved in favour of this document.