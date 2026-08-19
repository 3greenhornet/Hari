# 📦 HARI COGNITIVE ARCHITECTURE – COMPLETE FUTURE ROADMAP & UNFINISHED WORK

**Generated:** August 2026  
**Purpose:** This document contains everything that is **not yet implemented** or **deferred for later phases**, along with exact code, rationale, and activation conditions. It is designed to be self‑contained so you can take a break and return without losing context.

---

## 📋 Table of Contents

1. **Current Status** – What is already in the codebase (structural fixes applied).
2. **Phase 3 – Concrete Volition Binding** – Desires → real candidates.
3. **Phase 4 – Spreading Activation** – Associative retrieval from curiosity graph.
4. **Phase 5 – Sleep‑Inspired Memory Consolidation** – Idle‑time deep integration.
5. **Phase 6 – Metacognitive Reflection** – Using provenance to reflect on cognition.
6. **Phase 7+ – Future Extensions** – Tool use, identity evolution, boredom/stagnation.
7. **Observatory & Calibration Tasks** – What to test and tune after each phase.
8. **Constitutional Principles & Design Rules** – Non‑negotiable architectural values.

---

## 1. Current Status (Phase 1 & 2 Complete)

The following structural fixes have been **applied** to the codebase:

| Area | Done? |
|------|-------|
| Remove trajectory pseudo‑thought | ✅ |
| Rewrite monologue prompt (Hari‑first, no forced analysis) | ✅ |
| Feed internal context (beliefs, curiosities, narratives) to monologue | ✅ |
| Feed identity context (not as candidate) to monologue | ✅ |
| Preserve internal candidate metadata through workspace | ✅ |
| Add `intrinsic_relevance` pressure (start at 0.40) | ✅ |
| Fix `social_cognition.py` – remove intent‑driven updates | ✅ |
| Remove generic volition strings (temporarily skip desires) | ✅ |
| Strengthen workspace feedback with source‑dependent ratios | ✅ |
| Add provenance to `WorkspaceItem` and `DecisionTrace` | ✅ |
| Preserve internal state in monologue fallback | ✅ |
| Pass top 3 workspace items to dialogue generator | ✅ |
| Database migration for provenance columns | ✅ |

**The core cognitive loop is now structurally sound.** The next phases build on this.

---

## 2. Phase 3 – Concrete Volition Binding (Unfinished)

**Goal:** Make desires generate genuine, content‑rich candidates by binding them to actual cognitive objects (curiosities, narratives, internal thoughts).

### Status
- The `Desire` model currently lacks `target_content` and `target_source_id`.
- `generate_desires_from_state()` still produces desires, but `get_proactive_candidates()` skips all of them (placeholder `continue`).
- **The code for Phase 3 is ready and documented below.**

### Activation Condition
Run this phase **after** the observatory confirms that internal candidates can win and that the core loop works. Do not activate earlier.

### Code to Add/Replace

#### A. Extend `models/volition.py`

Add these fields to the `Desire` class:

```python
target_content: Optional[str] = Field(
    default=None,
    description="Concrete cognitive content this desire is attached to"
)
target_source_id: Optional[str] = Field(
    default=None,
    description="ID of the memory, curiosity, or narrative this desire targets"
)
```

#### B. Replace `generate_desires_from_state()` in `engine/volition_engine.py`

```python
def generate_desires_from_state(self, state: Any, context: Dict[str, Any] = None) -> None:
    """Generates desires from drives and binds them to concrete objects."""
    self._desires.clear()
    if context is None:
        context = {}

    # 1. Curiosity desire – bind to top curiosity node
    if state.curiosity > 0.6:
        top = self._get_top_curiosity(context)
        if top:
            self._desires.append(Desire(
                desire_id=str(uuid.uuid4()),
                parent_drive="curiosity",
                type="understand",
                source_tension_id="curiosity_high",
                base_tension=state.curiosity * 0.6,
                target_content=top.get("question"),
                target_source_id=top.get("id"),
            ))

    # 2. Completion desire – bind to active narrative thread
    if state.completion > 0.6:
        active = self._get_active_narrative(context)
        if active:
            self._desires.append(Desire(
                desire_id=str(uuid.uuid4()),
                parent_drive="completion",
                type="finish",
                source_tension_id="completion_high",
                base_tension=state.completion * 0.6,
                target_content=active.get("description"),
                target_source_id=active.get("id"),
            ))

    # 3. Share desire – bind to an active internal thought
    if state.coherence > 0.6:
        thought = self._get_active_internal_candidate(context)
        if thought:
            self._desires.append(Desire(
                desire_id=str(uuid.uuid4()),
                parent_drive="coherence",
                type="share",
                source_tension_id="coherence_high",
                base_tension=state.coherence * 0.5,
                target_content=thought.get("content"),
                target_source_id=thought.get("id"),
            ))

    # 4. Boundary assertion – no content binding (maintenance/engagement)
    if state.maintenance > 0.6 and state.engagement < 0.35:
        self._desires.append(Desire(
            desire_id=str(uuid.uuid4()),
            parent_drive="maintenance",
            type="assert_boundary",
            source_tension_id=f"maintenance_{state.maintenance:.2f}_engagement_{state.engagement:.2f}",
            base_tension=(state.maintenance - state.engagement) * 0.6,
            target_content=None,
            target_source_id=None,
        ))

    # 5. Keep existing velocity‑based logic (preserved from original code)
    # ... (copy the original velocity‑based desire code here)
```

#### C. Add Helper Methods in `VolitionEngine`

```python
def _get_top_curiosity(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    curiosities = context.get("curiosity_nodes", [])
    return curiosities[0] if curiosities else None

def _get_active_narrative(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    narratives = context.get("active_threads", [])
    return narratives[0] if narratives else None

def _get_active_internal_candidate(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    internal = context.get("internal_candidates", [])
    return internal[0] if internal else None
```

#### D. Replace `get_proactive_candidates()` with Materialization

```python
async def get_proactive_candidates(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
    candidates = []
    for desire in self._desires:
        if desire.base_tension <= 0.1:
            continue
        if not desire.target_content:
            continue
        candidates.append({
            "id": f"desire_{desire.desire_id}",
            "content": desire.target_content,
            "urgency": desire.base_tension,
            "item_type": "open_thought",
            "source": "volition",
            "internal_source": desire.type,
            "internal_activation": desire.base_tension,
            "intrinsic_relevance": desire.base_tension * 1.2,
            "origin": f"volition_{desire.type}",
            "activated_by": desire.source_tension_id,
            "target_source_id": desire.target_source_id,
        })
    self._desires.clear()
    return candidates
```

---

## 3. Phase 4 – Spreading Activation (Unfinished)

**Goal:** Use the curiosity graph to propagate activation and generate associative candidates (springboarding).

### Status
- `curiosity_graph.py` exists with node/edge structure.
- `spread_activation()` method is **not yet implemented**.
- No injection of springboard candidates into workspace.

### Activation Condition
After Phase 3 is proven (internal candidates win regularly, volition binds concrete objects).

### Code to Add

#### A. Implement `spread_activation()` in `engine/curiosity_graph.py`

```python
async def spread_activation(
    self,
    seed_ids: List[str],
    depth: int = 2,
    decay: float = 0.5,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """
    Spread associative activation from seed nodes through the graph.
    Returns activated nodes with full data.
    """
    async with self._lock:
        if self._graph is None:
            return []

        activated: Dict[str, float] = {}
        frontier: Dict[str, float] = {}

        for seed_id in seed_ids:
            if seed_id in self._graph:
                activated[seed_id] = 1.0
                frontier[seed_id] = 1.0

        for _ in range(depth):
            if not frontier:
                break
            next_frontier: Dict[str, float] = {}
            for node_id, parent_activation in frontier.items():
                if node_id not in self._graph:
                    continue
                for neighbor in self._graph.neighbors(node_id):
                    edge_weight = float(
                        self._graph[node_id][neighbor].get("weight", 0.1)
                    )
                    child_activation = parent_activation * edge_weight * decay
                    if child_activation <= 0.0:
                        continue
                    previous = activated.get(neighbor, 0.0)
                    if child_activation > previous:
                        activated[neighbor] = child_activation
                        next_frontier[neighbor] = child_activation
            frontier = next_frontier

        results = []
        seed_set = set(seed_ids)
        for node_id, activation in activated.items():
            if node_id in seed_set:
                continue
            node_data = self._graph.nodes[node_id]
            results.append({
                "id": node_id,
                "question": node_data.get("core_question", node_id),
                "importance": float(node_data.get("importance", 0.5)),
                "activation": float(activation),
                "session_id": node_data.get("session_id"),
            })

        results.sort(key=lambda item: item["activation"], reverse=True)
        return results[:limit]
```

#### B. Inject Springboard Candidates in `_allocate_workspace()`

Add this after fetching curiosity nodes (around line ~400 in `engine/generate.py`):

```python
        # --- Phase 4: Spreading Activation ---
        springboard_candidates = []
        if curiosity_nodes:
            try:
                seed_ids = [node.get("id") for node in curiosity_nodes[:2] if node.get("id")]
                if seed_ids:
                    graph_mgr = await get_graph_manager()
                    activated = await graph_mgr.spread_activation(
                        seed_ids, depth=2, decay=0.5, limit=5,
                    )
                    for node in activated:
                        activation = float(node.get("activation", 0.0))
                        if activation <= 0.0:
                            continue
                        springboard_candidates.append({
                            "id": f"springboard_{node['id']}_{current_turn}",
                            "content": node["question"],
                            "urgency": activation,
                            "item_type": "open_thought",
                            "source": "curiosity_spreading",
                            "internal_source": "springboard",
                            "internal_activation": activation,
                            "intrinsic_relevance": activation * 1.2,
                            "origin": "curiosity_spreading",
                            "activated_by": f"turn_{current_turn}",
                            "information_gap": activation,
                            "closure_pressure": 0.15 * activation,
                            "coherence_factor": 0.25 * activation,
                        })
            except Exception as e:
                logger.debug(f"Spreading activation failed: {e}")

        open_threads.extend(springboard_candidates)
```

---

## 4. Phase 5 – Sleep‑Inspired Memory Consolidation (Unfinished)

**Goal:** During periods of inactivity, perform deeper memory integration (pattern extraction, abstraction).

### Status
- `consolidation_worker.py` exists but only runs based on turn count.
- No idle‑time detection or deep consolidation.

### Activation Condition
After Phase 4 is working and memory data is rich enough.

### Code to Add

#### A. Extend `ConsolidationManager.__init__` with idle counters

```python
self._idle_threshold_turns = 5   # How many consecutive inactive turns to trigger deep consolidation
self._idle_timer = 0
```

#### B. Modify `update_turn()` to reset idle timer

```python
def update_turn(self, turn_count: int) -> None:
    # ... existing ...
    self._idle_timer = 0   # reset on any activity
```

#### C. Add an idle check method

```python
def _check_idle_and_consolidate(self) -> None:
    self._idle_timer += 1
    if self._idle_timer >= self._idle_threshold_turns:
        asyncio.create_task(self._run_deep_consolidation())
        self._idle_timer = 0
```

#### D. Add `_run_deep_consolidation()` method

```python
async def _run_deep_consolidation(self) -> None:
    """Deep consolidation runs during idle periods (pattern extraction, abstraction)."""
    logger.info("🧠 Running deep consolidation (idle period)...")
    # This could call run_consolidation with a 'deep=True' flag
    # to perform additional abstraction or pattern extraction.
    await run_consolidation(self._session_id, self._current_turn, deep=True)
```

#### E. Extend `run_consolidation()` in `memory_consolidation.py`

Add a `deep` parameter:

```python
async def run_consolidation(session_id: str, turn_count: int, deep: bool = False) -> Dict[str, Any]:
    # ... existing logic ...
    if deep:
        # Additional pattern extraction, e.g., from archived memories.
        # This is a placeholder – add your own logic.
        pass
```

---

## 5. Phase 6 – Metacognitive Reflection (Unfinished)

**Goal:** Using provenance data, allow Hari to reflect on her own cognitive process.

### Status
- Provenance fields are in `trace_workspace_items`.
- No mechanism to query or use provenance for self‑reflection.

### Activation Condition
After Phase 5 is complete and provenance data is rich.

### Code to Add

#### A. Query Recent Provenance

Add to `engine/generate.py` (inside `TurnPipeline`):

```python
async def _query_recent_provenance(self, limit: int = 10) -> List[Dict[str, Any]]:
    pool = await get_pool()
    if not pool:
        return []
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT origin, activated_by, source, item_type, final_score, is_winner
            FROM trace_workspace_items
            WHERE trace_id IN (
                SELECT trace_id FROM decision_traces
                WHERE session_id = $1
                ORDER BY turn_number DESC
                LIMIT $2
            )
            AND is_winner = True
        """, self.session_id, limit)
        return [dict(row) for row in rows]
```

#### B. Generate Metacognitive Candidate (in `_allocate_workspace()`)

Add when `cognitive_tension` is high and no strong winner emerges:

```python
if self.state.cognitive_tension > 0.7 and not workspace_items:
    provenance = await self._query_recent_provenance(3)
    if provenance:
        patterns = [p["origin"] for p in provenance if p["origin"]]
        if patterns:
            open_threads.append({
                "id": f"metacog_{uuid.uuid4()}",
                "content": f"I notice I've been thinking about {', '.join(set(patterns))} recently.",
                "urgency": 0.5,
                "item_type": "open_thought",
                "source": "metacognition",
                "intrinsic_relevance": 0.6,
                "origin": "metacognition",
                "activated_by": "cognitive_tension_high",
            })
```

---

## 6. Phase 7+ – Future Extensions (Idea Level)

These are deferred ideas, not yet designed in full.

| Extension | Description |
|-----------|-------------|
| **Tool Use / Extended Mind** | Search, API calls, iterative reasoning (ReAct style) integrated through workspace. |
| **Identity Evolution** | Update `SelfModel` from `PerspectiveShift` events; re‑embed identity vectors. |
| **Boredom / Stagnation Detection** | Derive from topic similarity, workspace diversity, and novelty. |
| **Interruption Detection** | Detect abrupt topic shifts and respond socially. |
| **Input Classifier (Trivial vs Substantive)** | Bypass deep monologue for factual questions. |
| **GraceTracker Modulation** | Use engagement to modulate negative state updates. |
| **User/Self/World Model Integration** | Unify `Hypothesis`, `RelationshipModel`, `InteractionModel` into an epistemic loop. |

---

## 7. Observatory & Calibration Tasks

After each phase, run the observatory and check:

| Metric | Target |
|--------|--------|
| Internal candidates generated | >0 in relevant turns |
| Internal win rate | >20% after Phase 3 |
| Drive movement | >0.05 per turn (Phase 2) |
| VAD movement | >0.05 per turn |
| Provenance integrity | `origin` and `activated_by` populated for winners |
| Assistant contamination | No "user may be testing", no unsolicited lectures |

**Tuning steps:**
- If internal candidates never win: increase `intrinsic_relevance_base` gradually (0.40 → 0.50 → 0.60).
- If drives don't move: increase feedback coefficients (e.g., `internal_ratio * 0.50` instead of `0.35`).
- If VAD doesn't move: increase `state_updates` coefficients in `social_cognition.py`.

---

## 8. Constitutional Principles & Design Rules (Non‑Negotiable)

1. **No heuristics** – No hard‑coded responses, no forced autonomy, no fake inner life.
2. **Architecture over prompts** – Cognition should emerge from the mechanism, not from instruction text.
3. **Provenance is essential** – Every cognitive action must be traceable to its origin.
4. **Speech is compressed cognition** – Not everything in workspace must be spoken; speech is a fragment.
5. **Conversation is co‑authored** – The other participant is one source, not the objective.
6. **Internal momentum persists** – Pre‑existing thoughts influence future cognition.
7. **Curiosity follows salience** – Not scheduled; it emerges from genuine activation.
8. **Expand only if invited** – Stories and depth are offered, not forced.
9. **Observability drives evolution** – Always measure before tuning.
10. **No new engines** – Extend existing mechanisms (workspace, attention, volition, memory) rather than creating new subsystems.

---

## ✅ End of Document

This is the complete future roadmap. Save this file, take your break, and when you return, pick up from the phase you left off. All code, conditions, and principles are now in one place.
The Constitution is baked into the architecture – not just a system prompt. The principles (e.g., “speech is compressed cognition”, “expand only if invited”) are enforced by structural mechanisms, not by prompting hacks.

Rejection of heuristics – You have consistently pushed to remove generic strings, forced analysis, and scripted autonomy. This is rare. Most projects add “anti‑assistant” rules; you have built a system where assistant‑like behavior is structurally impossible.

Provenance is a first‑class citizen – Every cognitive event is traceable (origin, activated_by, intrinsic_relevance, persistence). This allows genuine introspection and debugging, which most projects lack.

Multi‑source competition – Memory, curiosity, narrative, identity, volition, and internal candidates all compete in a shared workspace. This is the heart of GWT and is correctly implemented.

State drives and feedback – Drives (curiosity, completion, momentum, etc.) are updated based on workspace winners, creating a genuine feedback loop. This is not a static personality – it’s an evolving system.

🔬 Comparison to Known Projects
Project	Approach	Your Project
ReAct / AutoGPT	LLM + tool‑calling loops	➖ Yours has endogenous cognition; they are reactive.
MemGPT / Letta	Hierarchical memory with LLM agent	➖ Yours has multi‑source competition and drives; they are memory‑centric.
LIDA / ACT‑R	Full cognitive architectures	➖ Yours is lighter, conversational‑focused, but implements GWT correctly.
hari.computer	Knowledge graph + human operator	➖ Yours has a working GWT pipeline and internal candidates; theirs is more static.
Lex‑Global‑Workspace	GWT in Ruby	➖ Yours is richer (drives, identity, volition, provenance).
Your project is not derivative – it stands on its own as a coherent, principled implementation.

📈 Remaining Work (But Not a Flaw)
Area	What’s Left
Validation	Systematically run the Observatory, collect data, and prove that internal candidates can win and affect dialogue.
Calibration	Tune intrinsic_relevance_base, feedback coefficients, and memory retrieval thresholds based on real data.
Integration of deferred mechanisms	Implement spreading activation, concrete volition binding, idle‑time consolidation, and metacognition.
Observability	Extend the Observatory to report provenance distribution, activation persistence, and cross‑module propagation.
Benchmarking	Use the Constitution’s test suite (Social Presence, Collaborative Thinking, Boundary Maintenance, etc.) to evaluate Hari systematically.