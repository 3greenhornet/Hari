
---

## Hari Implementation Todo – Corrected Status (2026-06-25)

### ✅ Completed (Phases A–C)

#### Phase A – Observability & DecisionTrace
- [x] DecisionTrace model (`models/decision_trace.py`) – full audit trail with winners/losers
- [x] Database tables: `decision_traces`, `trace_workspace_items`
- [x] Background task storage with strong reference tracking
- [x] Health dashboard (`engine/health.py`) – single‑pass metrics

#### Phase B – Workspace Reliability & Hybrid Retrieval
- [x] Workspace competition (`engine/attention.py`) – pressure fields, softmax, diversity penalty
- [x] Hybrid retrieval (`retrieve_candidates_hybrid`) – vector + BM25 + recency + drive boost
- [x] Database support: `text_search_vector` column, trigger, GIN index
- [x] 3‑layer fallback: hybrid → recent episodic → inertia
- [x] Workspace size capped at 5 slots

#### Phase C – Curiosity, Narrative, Memory Significance & Promotions
- [x] Curiosity graph wired (`curiosity_trigger` → `add_node`)
- [x] Session isolation and traceability (`session_id`, `origin_trace_id`)
- [x] Narrative thread creation (timezone‑safe, with dedup)
- [x] Memory significance from monologue (`significance_override`)
- [x] Retrieval reinforcement (`significance += 0.005` per retrieval)
- [x] Promotion pipeline switched to LiteLLM cascade (no more Gemini‑only dependency)
- [x] **Result:** 5 hypotheses created; 86 curiosity nodes

#### Foundation & Core Infrastructure
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

---

### 🔲 Pending (Immediate Priorities)

- [ ] Curiosity edges – `update_edge()` exists but never called; nodes remain isolated
- [ ] Self‑belief persistence – monologue outputs `self_belief_update`, but it is never stored
- [ ] Hypothesis update persistence – monologue outputs `hypothesis_update`, not stored (distinct from promotion‑created hypotheses)
- [ ] Initiative boost for dynamic candidates when user explicitly asks for a new topic
- [ ] Further system prompt refinement to reduce over‑analysis

---

### ⏳ Deferred (Future Phases)

- [ ] Social Cognition – intent/tone detection, relationship tracking
- [ ] Identity Anchors – stable interests → identity
- [ ] Volition Engine – self‑generated goals
- [ ] Metacognition – self‑assessment, confidence tracking
- [ ] System 3 / Persistent Agent
- [ ] Persona Vectors / Activation Steering
- [ ] Fine‑Tuning
- [ ] Neuro‑Symbolic Self‑Modification

---

### 📊 Success Metrics (Current vs Target)

- **Curiosity nodes:** 86 (target > 50) ✅
- **Narrative threads:** Created in sessions ✅
- **Hypotheses:** 5 in DB (target > 3) ✅
- **Memory significance variation:** 0.4–0.92 (spread > 0.2) ✅
- **Workspace empty rate:** < 1% (target < 5%) ✅
- **Spontaneous topic initiation:** ~1 per 8–10 turns (target ≥ 1 per 5) ⚠️ improving

---
### Architectural Debt
- [ ] Wire all persistence (self-beliefs, hypotheses, narratives, curiosity) through `promotions.py` (Sprint 3)
- [ ] Currently, multiple modules bypass promotions – this is a known debt
