# Hari Implementation Todo

## Phase 1 – Complete (current scaffold)
- [x] State engine with asymptotic update
- [x] Cascades (fatigue, sovereignty, coherence, completion, horizon)
- [x] Grace system (rolling engagement)
- [x] Lightweight REPL with Gemini Pro
- [x] Environment config and fallbacks

## Phase 2 – Memory + Embeddings
- [ ] Implement pgvector schema (memories table with session_id)
- [ ] Add embedding function using `models/embedding-001`
- [ ] `engine/memory.py` – store and retrieve similar memories
- [ ] Modify `generate_hari_response` to retrieve top-3 memories and inject into prompt
- [ ] Add prediction error: expected vs actual user input (cosine distance)

## Phase 3 – Attention & Workspace
- [ ] `engine/attention.py` – salience formula (thematic_relevance, importance, completion, decay)
- [ ] Workspace (5 slots) loaded with top-salience items (memories, curiosity nodes, hypotheses)
- [ ] Inject workspace into Stage 2 prompt

## Phase 4 – Curiosity Graph & Narrative
- [ ] NetworkX graph for curiosity nodes
- [ ] Decay and edge weight updates
- [ ] Narrative state (current_arc, unresolved_questions)

## Phase 5 – Structured Monologue (Stage 1 JSON)
- [ ] Gemini Flash prompt that outputs deltas, finish_thought_first, curiosity_trigger
- [ ] Replace simple length-based deltas with LLM-derived deltas

## Phase 6 – Consolidation & Tuning
- [ ] Background thread for memory promotion, graph decay
- [ ] Litmus tests (continuity, grace recovery, memory recall)
