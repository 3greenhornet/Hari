# Hari – Roadmap & Current Status

**This is the single source of truth** for Hari's current status, completed work, and upcoming plans. All other documents link here.

Last Updated: 2026-07-04

---

## 🎯 Current Architectural Focus

The project is transitioning from independently functioning cognitive modules into an **integrated cognitive architecture**. Current work is focused on **behavioural calibration**—making the system feel authentic, coherent, and non‑assistant in live conversation.

**Current priorities:**
- Behaviour calibration (system prompt, attention coefficients, salience, feedback)
- Natural, reciprocal conversation (reduce mirroring, increase initiative)
- Stable attention dynamics (workspace competition, pressure fields)
- Identity integration (projection, self‑beliefs, origin context)

**Deliberately NOT focusing on:**
- New cognitive modules (contradictions, interests, volition)
- Long‑term planning or goal formation
- Multi‑agent systems or fine‑tuning
- Performance optimisation or throughput

---

## ⚠️ Current Risks

| Risk | Likelihood | Impact | Mitigation |
|:-----|:-----------|:-------|:-----------|
| Behaviour calibration may require multiple tuning passes | Medium | Delays Sprint 2.1C | Use DecisionTrace analytics (Ticket 021) for data‑driven tuning |
| Identity projection may not hold over long conversations | Medium | Inconsistent persona | Validate with behavioural regression and long‑turn tests |
| Attention coefficients remain manually tuned | High | Suboptimal workspace selection | Calibrate via experiments and pattern analysis |
| Structural persistence still bypasses promotions | Low | Architectural debt accumulates | Address in Sprint 3 (Ticket 017‑020) |

---

## 🔒 Current Constraints

These constraints explain architectural decisions and prevent wasted effort on impossible solutions.

| Constraint | Why |
|:-----------|:----|
| **API‑based LLMs only** | No local model hosting; no access to internal activations |
| **No model fine‑tuning** | All behaviour comes from architecture and prompts, not weight updates |
| **Single conversational thread** | No parallel conversations or multi‑session context (by design) |
| **Session‑scoped identity** | Each session is a fresh Hari; cross‑session memory is optional |
| **No autonomous execution** | Hari only responds to user prompts; no background thoughts |

---

## 📋 Current Sprint: 2.1C – Behaviour Calibration (In Progress)

| Ticket | Description | Priority | Status |
|:-------|:------------|:---------|:-------|
| 009 | Tune system prompt (neutral, reciprocal, non‑assistant) | High | ⏳ Pending |
| 010 | Calibrate attention coefficients | Medium | ⏳ Pending |
| 011 | Add exploratory potential to salience formula | Medium | ⏳ Pending |
| 012 | Add shared significance to salience formula | Low | ⏳ Pending |
| 013 | Strengthen `broadcast_feedback` coefficients | Medium | ⏳ Pending |

**Exit Criteria for Sprint 2.1C:**
- [ ] Mirroring no longer commonly observed in 20‑turn conversations.
- [ ] Hari initiates at least one spontaneous topic every 5 turns on average.
- [ ] Attention coefficients remain stable across 50+ conversation turns.
- [ ] Behavioural regression suite passes with expected improvements.

---

## 📈 Success Metrics

### System Health Metrics

| Metric | Current | Target | Status |
|:-------|:--------|:-------|:-------|
| Workspace empty rate | < 1% | < 5% | ✅ |
| Memory retrieval latency | TBD | < 500ms | ⏳ Needs measurement |
| Curiosity graph density | 0 edges | > 0.01 | ⏳ Improving (Ticket 006) |
| DecisionTrace coverage | > 80% | > 90% | ✅ |

### Behavioural Metrics

| Metric | Current | Target | Status |
|:-------|:--------|:-------|:-------|
| Spontaneous topic initiation | ~1 per 8‑10 turns | ≥ 1 per 5 | ⚠️ Improving |
| Mirroring frequency | Occasional | Rare | ⚠️ Tuning needed |
| Identity consistency (over 20 turns) | Not yet measured | High | ⏳ Planned |
| Narrative persistence | Threads created | Avg. lifespan > 10 turns | ⏳ Improving |

---

## 🧪 Evaluation Status

| Test Suite | Status | Notes |
|:-----------|:-------|:------|
| Unit tests (`test_state.py`) | ✅ Complete | Covers state mechanics |
| Behavioural tests (`test_behavior.py`) | ⚠️ Partial | Needs real LLM mocking and async markers |
| G‑Eval qualitative evaluation | ✅ Complete | 4 rubrics (continuity, coherence, anti‑assistant, curiosity) |
| Long conversation benchmarks | ❌ Not Started | Planned for Sprint 2.1C |
| Identity consistency evaluation | ❌ Planned | Planned for after Sprint 2.1C |

---

## 🚧 Known Architectural Debt

| Category | Debt | Exit Strategy | Target Sprint |
|:---------|:-----|:--------------|:--------------|
| **Architecture** | Narrative threads bypass `promotions.py` | Move all structural creation through promotions | Sprint 3 |
| **Architecture** | `broadcast_feedback()` mutates state directly | Introduce `CognitiveRuntime` state authority | Sprint 2.1C or 3 |
| **Architecture** | `IdentityModel()` constructed inline | Introduce `IdentityManager` | Sprint 3+ |
| **Implementation** | Hypothesis classification uses `type="world"` | Replace with structured `HypothesisUpdate` | 2.1D or 3 |
| **Implementation** | HNSW index removal (commented out) | Revisit when pgvector supports 3072 | Future |

---

## 🗺️ Upcoming Sprints

### Sprint 2.1D – Social Cognition

| Ticket | Description | Priority |
|:-------|:------------|:---------|
| 014 | Extend monologue for avoidance pattern detection | Medium |
| 015 | Wire social interpretation into state updates | Medium |
| 016 | Implement relationship model loading/updating | Low |

### Sprint 3 – Ecology Pipeline

| Ticket | Description | Priority |
|:-------|:------------|:---------|
| 017 | Contradiction detection | High |
| 018 | Interest formation (curiosity → interest) | High |
| 019 | Identity evolution (interests → identity anchors) | Medium |
| 020 | Volition engine (desires → agendas) | Low |

---

## 📜 Architectural Milestones (Completed)

### Phase A – Observability & DecisionTrace
- [x] DecisionTrace model (`models/decision_trace.py`) – full audit trail with winners/losers
- [x] Database tables: `decision_traces`, `trace_workspace_items`
- [x] Background task storage with strong reference tracking
- [x] Health dashboard (`engine/health.py`) – single‑pass metrics

### Phase B – Workspace Reliability & Hybrid Retrieval
- [x] Workspace competition (`engine/attention.py`) – pressure fields, softmax, diversity penalty
- [x] Hybrid retrieval (`retrieve_candidates_hybrid`) – vector + BM25 + recency + drive boost
- [x] Database support: `text_search_vector` column, trigger, GIN index
- [x] 3‑layer fallback: hybrid → recent episodic → inertia
- [x] Workspace size capped at 5 slots

### Phase C – Curiosity, Narrative, Memory Significance & Promotions
- [x] Curiosity graph wired (`curiosity_trigger` → `add_node`)
- [x] Session isolation and traceability (`session_id`, `origin_trace_id`)
- [x] Narrative thread creation (timezone‑safe, with dedup)
- [x] Memory significance from monologue (`significance_override`)
- [x] Retrieval reinforcement (`significance += 0.005` per retrieval)
- [x] Promotion pipeline switched to LiteLLM cascade (no more Gemini‑only dependency)
- [x] **Result:** 5 hypotheses created; 86 curiosity nodes

### Foundation & Core Infrastructure
- [x] State engine (`psyche/state.py`) – drives, VAD, asymptotic updates
- [x] Cascades – fatigue, sovereignty, coherence, completion, horizon
- [x] Grace system – rolling engagement tracker
- [x] Monologue fallback – Groq (resolved Gemini 429 quota)
- [x] LiteLLM async integration (`acompletion`)
- [x] Embedding dimension fix (768 → 3072)
- [x] Memory serialization (`json.dumps` / `json.loads` for asyncpg)
- [x] System prompt leakage fixed (no raw drives/workspace in dialogue)
- [x] `broadcast_feedback` expanded (halved coefficients; now touches curiosity, coherence, engagement, arousal, completion, valence)
- [x] Dynamic candidate injection (top‑2; occasionally wins workspace; e.g., jellyfish, synchronicity)
- [x] Mirroring significantly reduced through new `SYSTEM_INSTRUCTION` rules

### Completed Sprint: 2.1B – Architectural Wiring

| Ticket | Description | Status |
|:-------|:------------|:-------|
| 004 | Self‑belief persistence (`SelfBeliefManager`) | ✅ Done |
| 004A | Schema consistency (3072 dims, remove HNSW) | ✅ Done |
| 005 | Hypothesis updates (temporary `type="world"`) | ✅ Done |
| 006 | Curiosity edges (`observe_workspace`) | ✅ Done |
| 007 | Workspace context interpretation (natural language) | ✅ Done |
| 008 | Identity projection layer (`IdentityProjection`, renderer) | ✅ Done |

---

## 📚 Links

- **Architectural Constitution & Research Incubator:** `docs/research_incubator/README.md`
- **Project Map:** `PROJECT_MAP.md`
- **Architecture Details:** `ARCHITECTURE.md`

---

**All status information is maintained here. Update this file when sprints are completed or new tickets are added.**