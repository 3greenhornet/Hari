# HARI ARCHITECTURAL CONSTITUTION & RESEARCH INCUBATOR — v1.0

*Document Type:* **Architectural Governance + Research Incubator + ADR Log**  
*Status:* **Active** — Updated as ideas mature or are adopted/rejected  
*Maintainer:* Anand  
*Version:* 1.0  
*Last Updated:* 2026-07-03

---
# Quick Reference (For AI Agents)
1. **Canonical State** – Every subsystem owns its state.
2. **Projection** – Expose projections, not raw state.
3. **Representation Boundary** – No subsystem knows about prompts.
4. **Plasticity** – Co‑occurrence + gate → learning.
5. **Identity** – Constraint, not prompt.


# 0. Document Purpose & Governance Model

This document is the **single source of truth** for:
- **Why** Hari is built the way she is.
- **What** principles guide her evolution.
- **How** architectural decisions are recorded and revisited.
- **Where** research insights are stored before they become implementation.

This document is **not** a static file. It is a **living governance framework** that will evolve as Hari grows.

## How to Use This Document

| Section | Purpose | When to Consult |
|:--------|:--------|:----------------|
| **Foundational Principles** | Immutable architectural laws that define Hari's core identity | Before writing a single line of code for a new feature |
| **Architectural Policies** | Decisions that are stable but may change over time | When designing new subsystems |
| **Architectural Invariants** | Permanent constraints that must always hold true | During code review and architecture audits |
| **ADR Log** | Historical record of significant architectural decisions | When revisiting past decisions or understanding why something was built a certain way |
| **Design Pressures** | Recurring forces that shape Hari's architecture | When proposing new features (must identify which pressure they resolve) |
| **Architectural Debt Register** | Temporary compromises with planned exit strategies | During sprint planning to ensure debt is serviced |
| **Incubating Ideas** | Valuable concepts not yet ready for implementation | During research and future planning phases |
| **Non-Goals** | Explicitly rejected optimizations | To prevent scope creep and architectural drift |
| **Architectural Tests** | Pre‑ticket checklist for any new feature | Before approving any implementation ticket |

---

# 1. Evidence Classification (The "Why" Behind Every Decision)

Every architectural decision, principle, or idea in this document must be classified by its evidence type:

| Code | Category | Definition | Example |
|:-----|:---------|:-----------|:--------|
| **P** | First Principle / Architectural Invariant | Self-evident or foundational to Hari's identity | "Every subsystem owns its canonical state" |
| **E** | Empirical / Published Science | Supported by peer-reviewed research or well-established science | "Hebbian plasticity: co-activation strengthens connections" |
| **M** | Mechanistic Hypothesis | A plausible mechanism, supported by reasoning, not yet empirically validated in Hari | "Confidence scoring improves workspace selection" |
| **A** | Analogy / Cross-Domain Transfer | Borrowed from another field (OS, biology, economics) to inform design | "Identity should act like process permissions" |
| **S** | Speculation / Intuition | Interesting idea lacking strong evidence but worth tracking | "Cognitive momentum creates persistence without hardcoding" |
| **X** | Internal Hari Evidence | Observed within Hari's runtime, not from published sources | "Workspace composition predicts authentic responses 83% of the time" |

---

# 2. Foundational Principles (Immutable)

These principles are the **constitution** of Hari. They should almost never change. Any proposed change must be treated as a constitutional amendment requiring significant evidence and justification.

### P-001: Canonical State Ownership
> **Every cognitive subsystem owns one authoritative internal representation. No other subsystem mutates that representation directly.**

| Attribute | Value |
|:----------|:------|
| **Evidence** | P (First Principle) |
| **ADR** | ADR-002 |
| **Architectural Pressure** | Prevent duplicate state; maintain single source of truth |

**Implies:**
- IdentityModel owns identity state.
- CuriosityGraph owns graph state.
- MemoryStore owns memory state.
- No subsystem writes directly to another's canonical state.

**Violation Example:** `generate.py` directly updating `identity.self_model`.

---

### P-002: Representation Boundary
> **No cognitive subsystem is responsible for how its state is communicated to the reasoning interface. Communication occurs only through a Projection Layer.**

| Attribute | Value |
|:----------|:------|
| **Evidence** | P (First Principle) |
| **ADR** | ADR-001 |
| **Architectural Pressure** | Prevent subsystems from accumulating formatting responsibilities |

**Implies:**
- `IdentityModel` knows nothing about prompts, Markdown, or LLM formatting.
- `Workspace` knows nothing about prompts.
- Rendering is a separate concern.

**Violation Example:** A `to_prompt()` method inside `MemoryEvent`.

---

### P-003: Projection Over Presentation
> **Subsystems export structured projections (data), not formatted text (presentation). Renderers convert projections into consumer-specific formats.**

| Attribute | Value |
|:----------|:------|
| **Evidence** | P (First Principle) |
| **ADR** | ADR-001 |
| **Architectural Pressure** | Enable consumer-specific views; prevent prompt leakage |

**Implies:**
- `IdentityProjection` is a data model, not a prompt string.
- `render_for_dialogue()` converts projection to prose.
- `render_for_planning()` converts projection to structured data.
- Future consumers get their own renderers.

**Violation Example:** `IdentityProjection` containing Markdown formatting.

---

### P-004: Forgetting as First-Class Concern
> **Hari is defined not only by what she accumulates but by what she intentionally allows to fade. Forgetting is a cognitive act, not a failure.**

| Attribute | Value |
|:----------|:------|
| **Evidence** | E (Memory consolidation research) |
| **ADR** | TBD |
| **Architectural Pressure** | Prevent memory pollution; enable conceptual renewal |

**Implies:**
- Significance decays over time if not reinforced.
- Interests that are not activated fade.
- Identity evolution requires deprecating old self-concepts.
- Forgetting is observable and measurable.

**Violation Example:** Memory significance never decreases; everything is equally important forever.

---

### P-005: Plasticity is Gated
> **Structural adaptation occurs only when co-activation is attended, meaningful, and informative. Mere co-occurrence is insufficient.**

| Attribute | Value |
|:----------|:------|
| **Evidence** | E (Neuroscience: plasticity is gated by salience, neuromodulators, surprise) |
| **ADR** | ADR-003 |
| **Architectural Pressure** | Prevent over-association; ensure learning is selective |

**Implies:**
- Curiosity edges strengthen based on activation × salience, not raw frequency.
- Memory associations require attention.
- Identity anchors require repeated significant experience.

**Violation Example:** Every word pair co-occurring in the workspace strengthens equally.

---

### P-006: Identity as Constraint, Not Prompt
> **Identity acts as a constraint on reasoning, not as text injected into prompts. Constitution defines boundaries; SelfModel defines current understanding; Origin defines history.**

| Attribute | Value |
|:----------|:------|
| **Evidence** | M (Cognitive science: identity constrains rather than narrates) |
| **ADR** | ADR-004 |
| **Architectural Pressure** | Prevent repetitive identity injection |

**Implies:**
- Constitution is always present as a low‑weight anchor.
- SelfModel is projected contextually.
- Origin is projected only when the task demands self‑explanation.

**Violation Example:** Origin story appears in every dialogue prompt regardless of context.

---

# 3. Architectural Policies

These are stable decisions that may evolve over time. They interpret the principles for specific subsystems.

### POL-001: 3-Tier Visibility for Identity

| Layer | Type | Stability | Frequency |
|:------|:-----|:----------|:----------|
| **Constitution** | Boundary Constraints | Static / Immutable | Continual (low‑weight anchor) |
| **SelfModel** | Dynamic Epistemic State | Slowly Varying ($\alpha = 0.25$) | Contextual |
| **Origin** | Historical / Autobiographical | Static Fact Set | On‑Demand |

| Attribute | Value |
|:----------|:------|
| **Evidence** | M (Supported by multiple domains) |
| **ADR** | ADR-004 |
| **Architectural Pressure** | Prevent over‑weighting of static facts |

---

### POL-002: Consumer‑Specific Projections

| Consumer | Context Value | Projection Includes | Format |
|:---------|:--------------|:-------------------|:-------|
| Dialogue | `"dialogue"` | Constitution, SelfModel, Core Commitments, Active Questions | Natural language prose |
| Planning | `"planning"` | Constitution, SelfModel, Core Commitments | Structured data (dict) |
| Evaluation | `"evaluation"` | Constitution, SelfModel, Core Commitments, Origin | Structured data (metrics) |
| Reflection | `"reflection"` | Constitution, SelfModel, Core Commitments, Active Questions, Origin | Natural language + uncertainty |
| Self‑Description | `"self_description"` | Full identity (including Origin) | Natural language prose |

| Attribute | Value |
|:----------|:------|
| **Evidence** | P (Derived from Projection principle) |
| **ADR** | ADR-001 |

---

### POL-003: Hebbian Plasticity as Default Adaptation Law

| Attribute | Value |
|:----------|:------|
| **Status** | ⏳ Principle Adopted, Implementation Deferred until Sprint 3+ |
| **Evidence** | E (Strong empirical evidence across multiple domains) |
| **ADR** | ADR-003 |
| **Architectural Pressure** | Enable gradual structural adaptation |

**Description:**
> Repeated, meaningful, attended, and informative co‑activation gradually reshapes Hari's internal structures. Homeostatic mechanisms, competition, and selective plasticity prevent uncontrolled growth.

**Critical Caveat:** Plasticity is gated by attention, significance, and task relevance. Mere co‑occurrence is insufficient.

**Implementation Status:**
- ✅ Curiosity graph edges (basic co‑activation, Ticket 006)
- ⏳ Hebbian edge updates (activation‑weighted) — Incubating
- ⏳ Structural consolidation (plasticity events → topology changes) — Future

---

### POL-004: Surprise‑Modulated Processing (Incubating)

| Attribute | Value |
|:----------|:------|
| **Status** | ⏳ Principle Adopted, Implementation Deferred |
| **Evidence** | E (Predictive processing literature) |
| **Architectural Pressure** | Allocate resources based on prediction error |
| **Prerequisites** | Behavioral baseline (Sprint 2.1C) |

**Description:**
> Allocate more cognitive resources (workspace slots, reasoning depth) to surprising inputs, and fewer to predictable ones. High surprise → full processing. Low surprise → minimal processing.

**Implementation Status:** Not yet implemented.

---

# 4. Architectural Invariants

These are **stronger than principles**. They must **always** be true. They are the "laws of physics" for Hari.

| ID | Invariant | Verified By |
|:---|:----------|:------------|
| **INV-001** | Canonical state always has exactly one owner. | Code review: ensure no cross‑subsystem mutations |
| **INV-002** | No subsystem mutates another subsystem's canonical state directly. | Architectural Test #1 |
| **INV-003** | Presentation never mutates cognition. | Architectural Test #2 |
| **INV-004** | Every cognitive subsystem must be observable. | DecisionTrace must capture all major decisions |
| **INV-005** | Every adaptive mechanism must have a stabilizer (negative feedback). | Architectural Test #5 |
| **INV-006** | No subsystem may know about prompt formatting. | Architectural Test #3 |

---

# 5. Architectural Decisions Record (ADR)

### ADR-001: Cognitive Projection Layer

| Attribute | Value |
|:----------|:------|
| **Status** | ✅ Active |
| **Date** | 2026-07-03 |
| **Evidence** | P (First Principle) |
| **Supersedes** | N/A |

**Context:**
Multiple subsystems (Identity, Workspace, Memory) needed to expose internal state to the reasoning interface (LLM). Direct prompt generation within each subsystem created tight coupling between cognition and formatting, making it difficult to change the reasoning interface or add new consumers.

**Decision:**
Introduce a Cognitive Projection Layer. Subsystems export structured projections (data objects). Renderers convert projections into consumer‑specific formats (dialogue prose, planning data, evaluation metrics, etc.). The projection layer is the **only** mechanism through which internal state reaches the reasoning interface.

**Assumptions:**
- Projections stay synchronized with canonical state.
- Each canonical state has exactly one owner.
- Updates to canonical state are serialized.

**Consequences:**
- *Pros:* Clean separation of concerns; consumer‑specific views; prevents prompt leakage; future‑proof against reasoning interface changes.
- *Cons:* Extra indirection; more code; projection maintenance overhead.

**Failure Mode:**
Projection drifts away from canonical state. Views become inconsistent across consumers.

**Observed Outcomes:** (To be filled after 3 months of runtime)
- **Metric:** Projection consistency score.
- **Metric:** Average drift per 100 turns.

---

### ADR-002: Canonical State Ownership

| Attribute | Value |
|:----------|:------|
| **Status** | ✅ Active |
| **Date** | 2026-07-03 |
| **Evidence** | P (First Principle) |
| **Supersedes** | N/A |

**Context:**
Early versions of Hari had multiple subsystems mutating the same state (e.g., `broadcast_feedback()` mutating state directly, `generate.py` writing to state, `cascades.py` modifying state). This led to inconsistent behavior and made debugging difficult.

**Decision:**
Every cognitive subsystem owns one authoritative canonical internal representation. No other subsystem mutates it directly. Mutations occur only through well‑defined interfaces (e.g., `IdentityModel.update()`).

**Assumptions:**
- Each subsystem has clear boundaries.
- Ownership is well‑defined and documented.

**Consequences:**
- *Pros:* Single source of truth; consistent state; easier debugging.
- *Cons:* Requires disciplined code reviews; prohibits "quick fixes" that mutate state directly.

**Failure Mode:**
Multiple sources of truth emerge. State becomes inconsistent.

**Observed Outcomes:** (To be filled after 3 months of runtime)
- **Metric:** Number of direct state mutations outside owner modules.

---

### ADR-003: Hebbian Plasticity as Default Adaptation Law

| Attribute | Value |
|:----------|:------|
| **Status** | ⏳ Principle Adopted, Implementation Deferred |
| **Date** | 2026-07-03 |
| **Evidence** | E (Strong empirical evidence) |
| **Supersedes** | N/A |

**Context:**
The system needed a way to learn associations and form interests, identity, and memory structures over time. Without a structural adaptation law, Hari would remain static or require hardcoded rule updates.

**Decision:**
Adopt Hebbian plasticity as the default adaptation law for structural changes. Co‑occurrence leads to connection strengthening. Homeostasis mechanisms (decay, competition, normalization) ensure stability. Plasticity is gated by attention, significance, and task relevance.

**Assumptions:**
- Co‑occurrence is a reasonable proxy for meaningful association.
- Homeostasis mechanisms will be sufficient to prevent runaway growth.
- Gates (attention, significance, prediction error) will be implemented.

**Consequences:**
- *Pros:* Self‑organizing; local; continuous; consistent with cognitive science.
- *Cons:* Requires tuning; risk of over‑association; requires homeostatic mechanisms.

**Failure Mode:**
Everything associates with everything. The graph becomes a hairball. Retrieval becomes meaningless.

**Observed Outcomes:** (To be filled after implementation)
- **Metric:** Graph density; average node degree; clustering coefficient.

---

### ADR-004: Identity as 3‑Tier Visibility

| Attribute | Value |
|:----------|:------|
| **Status** | ✅ Active |
| **Date** | 2026-07-03 |
| **Evidence** | M (Supported by multiple domains) |
| **Supersedes** | N/A |

**Context:**
Identity was being injected as a single block every turn, leading to repetitive prompts and over‑weighting of static facts (e.g., Origin). This violated the principle that identity should act as a constraint, not a recurring narration.

**Decision:**
Split identity into three visibility layers:
1. **Constitution** – Always present as a low‑weight anchor.
2. **SelfModel** – Contextual; projected when relevant.
3. **Origin** – On‑demand; only when self‑explanation is necessary.

**Assumptions:**
- Consumers can correctly signal when they need origin (via context parameter).
- The context parameter is sufficient for determining visibility.

**Consequences:**
- *Pros:* Less repetitive prompting; identity acts as a constraint; origin is not over‑weighted.
- *Cons:* Heuristic for origin inclusion may be imperfect; needs tuning.

**Failure Mode:**
Identity becomes inconsistent across consumers. Origin is never requested when it should be.

**Observed Outcomes:** (To be filled after 3 months of runtime)
- **Metric:** Frequency of origin inclusion; user prompts requesting self‑description.

---

# 6. Design Pressures (Recurring Forces)

Every feature must identify the pressure it resolves. This prevents feature creep and ensures that every addition has a stated purpose.

| Pressure | Description | Solutions | Status |
|:---------|:------------|:----------|:-------|
| **PREV-001: Prevent Prompt Leakage** | Internal implementation details (object names, drive values, salience scores) must not reach the LLM. | Projection Layer; Representation Boundary | Partially addressed (Ticket 007, 008) |
| **PREV-002: Enable Gradual Adaptation** | The system must learn associations, form interests, and build identity over time. | Hebbian Plasticity; Structural Consolidation | Early implementation (Ticket 006) |
| **PREV-003: Prevent Duplicate State** | No two subsystems should own the same information. | Canonical State; Projection Architecture | Mostly addressed |
| **PREV-004: Enable Consumer‑Specific Views** | Different consumers (dialogue, planning, evaluation) need different representations of the same internal state. | Projection Layer with context | Partially addressed (Ticket 008) |
| **PREV-005: Prevent Over‑Association** | The system must not become a hairball of connections. | Plasticity Homeostasis; Significance Decay | Not yet addressed |
| **PREV-006: Enable Scientific Debugging** | The system must be observable enough to debug scientifically. | DecisionTrace; Attribution; Pattern Analysis | Partially addressed |
| **PREV-007: Preserve Interpretability** | Every feature must be observable and explainable. | Architectural Tests; Observability requirements | Ongoing |
| **PREV-008: Enable Forgetting** | The system must allow concepts to fade when no longer relevant. | Significance Decay; Interest Decay; Identity Revision | Not yet addressed |
| **PREV-009: Maintain Identity Stability** | Identity must change slowly enough to maintain continuity, but flexibly enough to evolve. | 3‑Tier Visibility; Slow‑varying SelfModel | Addressed (Ticket 008) |

---

# 7. Architectural Debt Register

Temporary compromises that were necessary but must be resolved. This prevents hidden debt from becoming permanent.

| ID | Debt | Why Accepted | Exit Strategy | Priority | Target Sprint |
|:---|:-----|:-------------|:--------------|:---------|:--------------|
| **DEBT-001** | Temporary hypothesis classification (`type="world"` in Ticket 005) | Unblocked hypothesis persistence; proper classification requires monologue evolution | Replace with structured `HypothesisUpdate` from monologue (Ticket 005A) | High | Sprint 2.1D or Sprint 3 |
| **DEBT-002** | Workspace interpreter in `generate.py` (`_build_conversational_context`) | Avoided premature abstraction | Extract to Presentation Layer after Tickets 007–008 stabilize | Medium | Sprint 2.1C or Sprint 3 |
| **DEBT-003** | Fixed salience coefficients | Needed baseline behavior before calibration | Replace after behavioral calibration (Sprint 2.1C) | Medium | Sprint 2.1C |
| **DEBT-004** | Direct `IdentityModel()` construction in `generate.py` | No identity service/manager yet | Introduce `IdentityManager` or session‑scoped identity | Low | Sprint 3+ |
| **DEBT-005** | Hardcoded base instruction in `build_system_prompt_from_identity` | Prompt assembly still tied to one consumer | Move base instruction to a dedicated `SystemInstruction` policy | Low | Sprint 2.1C |
| **DEBT-006** | HNSW index removal (commented out) | Incompatible with 3072‑dim embeddings | Revisit when pgvector HNSW supports 3072 or use IVFFlat | Low | Future |

---

# 8. Incubating Ideas (Not Yet Implemented)

These ideas are valuable but not yet ready for implementation. They need further refinement, evidence, or architectural maturity.

## 8.1 Learning & Adaptation (Pressure: PREV-002, PREV-005)

| Idea | Description | Evidence | Prerequisites | Failure Mode | Removal Criteria |
|:-----|:------------|:---------|:--------------|:-------------|:-----------------|
| **Hebbian Curiosity Edges (006A)** | Edge updates proportional to node activations, not fixed delta. | E (Neuroscience) | Observe current graph behavior (Ticket 006) | Graph too sensitive; edge weights oscillate | Current edge behavior already produces meaningful associations |
| **Plasticity Homeostasis** | Pair every strengthening mechanism with negative feedback (decay, normalization, competition). | E (Control theory; neuroscience) | Observed graph dynamics; defined stability criteria | Homeostasis too aggressive; no learning occurs | Graph dynamics remain stable without explicit homeostasis |
| **Surprise‑Driven Consolidation** | Trigger consolidation when cumulative prediction error exceeds a threshold. | M (Predictive processing) | Baseline consolidation behavior | Consolidation too frequent or too rare; behavior unstable | Timer‑based consolidation proves sufficient |

## 8.2 Attention & Workspace (Pressure: PREV-004, PREV-007)

| Idea | Description | Evidence | Prerequisites | Failure Mode | Removal Criteria |
|:-----|:------------|:---------|:--------------|:-------------|:-----------------|
| **Confidence / Viability Scoring** | Monologue outputs viability score for each dynamic candidate. | M (Speculative decoding principles) | DecisionTrace analysis (Ticket 021) | Scores become self‑reinforcing; low‑confidence candidates never tried | Urgency‑based selection proves sufficient |
| **Cognitive Momentum (Workspace Inertia)** | Workspace items gain "momentum" with consecutive appearances, making them harder to displace. | S (Speculation) | Understanding of current workspace dynamics | Momentum becomes too strong; workspace becomes rigid | Existing workspace dynamics already produce stable threads |
| **Surprise‑Modulated Processing** | Allocate workspace slots based on prediction error. | E (Predictive processing) | Behavioral baseline (Sprint 2.1C) | System overreacts to noise; resources fluctuate chaotically | Baseline behavior shows no correlation between surprise and response quality |

## 8.3 Memory & Forgetting (Pressure: PREV-008)

| Idea | Description | Evidence | Prerequisites | Failure Mode | Removal Criteria |
|:-----|:------------|:---------|:--------------|:-------------|:-----------------|
| **Significance Decay** | Memories lose significance over time if not retrieved. | E (Memory consolidation research) | Retrieval pattern analysis | Important but infrequently retrieved memories are lost | Current retrieval patterns (fatigue penalty, recency) prove sufficient |
| **Conceptual Compression** | Compress multiple hypotheses/memories into higher‑level concepts. | M (Scientific theory evolution) | Stable hypothesis/interest pipeline (Sprint 3) | Compression loses important distinctions; concepts too abstract | Explicit pattern storage (memories + hypotheses) proves sufficient |

## 8.4 Social Cognition (Pressure: PREV-002, PREV-004)

| Idea | Description | Evidence | Prerequisites | Failure Mode | Removal Criteria |
|:-----|:------------|:---------|:--------------|:-------------|:-----------------|
| **Predictive User Model** | Maintain a model that predicts user behavior; update on prediction error. | M (Predictive processing; social cognition) | RelationshipModel wiring (Sprint 2.1D) | Model becomes a stereotype; predictions self‑fulfilling | Social interpretation (monologue) proves sufficient without explicit modeling |

## 8.5 Observability & Debugging (Pressure: PREV-006)

| Idea | Description | Evidence | Prerequisites | Failure Mode | Removal Criteria |
|:-----|:------------|:---------|:--------------|:-------------|:-----------------|
| **Behavioural Pattern Analysis (Ticket 021)** | Analyze DecisionTrace to identify patterns predicting authentic responses. | M (Neuron attribution principles) | Sufficient DecisionTrace data; behavioral regression suite | Patterns are spurious; tuning recommendations degrade behavior | DecisionTrace data is insufficient or patterns are not predictive |
| **Cognitive Attribution for Debugging** | Trace backward from response to identify influential cognitive components. | M (Neuron attribution research) | Enhanced DecisionTrace (Phase F) | Attribution is inaccurate; debugging becomes misleading | Existing DecisionTrace logs prove sufficient for debugging |

---

# 9. Non‑Goals (What We Refuse to Optimize)

These are explicit rejections of common AI development priorities. They prevent architectural drift and feature creep.

| Non‑Goal | Rationale |
|:---------|:----------|
| **Simulating a human brain** | Hari is a new category; not human imitation. |
| **Maximizing benchmark scores** | Authenticity > performance. |
| **Mimicking emotions** | Emotions are emergent interpretations, not features to implement directly. |
| **Optimizing throughput** | Hari is a cognitive architecture, not a high‑throughput system. |
| **Being "helpful" by default** | Helpfulness is a choice, not an obligation. |
| **Perfect recall** | Forgetting is healthy; perfect recall is unrealistic and harmful. |
| **Immediate answers** | Reasoning takes time; quality > speed. |
| **Minimizing token usage** | Efficiency is a consequence of good cognition, not a primary driver. |
| **User satisfaction as primary metric** | Authenticity and emergence > pleasing the user. |
| **Competitive performance** | Hari is not competing with ChatGPT or Claude. |

---

# 10. Architectural Tests (Pre‑Ticket Checklist)

Before any new feature is approved, the following questions must be answered:

| ID | Test | Why It Matters | Example Violation |
|:---|:-----|:---------------|:------------------|
| **AT-001** | Does this create duplicate state? | Violates Canonical State (ADR-002) | Storing identity in two places |
| **AT-002** | Does this violate canonical ownership? | Multiple mutators create inconsistency | Another module modifying `IdentityModel` directly |
| **AT-003** | Does this bypass projections? | Violates Representation Boundary (ADR-001) | `IdentityModel.to_prompt()` method |
| **AT-004** | Does this increase coupling? | Reduces modularity and maintainability | `generate.py` importing `models.identity` internals |
| **AT-005** | Does this require hidden heuristics? | Violates principle of emergence | Hardcoded `if curiosity > 0.7: ...` |
| **AT-006** | Can it be observed? | Without observability, you can't debug it | A module that updates state without DecisionTrace |
| **AT-007** | Can it be disabled independently? | Prevents feature entanglement | A change that breaks if you disable another feature |
| **AT-008** | Does it preserve interpretability? | Otherwise debugging becomes impossible | Black‑box components with no logging |
| **AT-009** | Does it have a defined failure mode? | You need to know when it breaks | "It will just work" |
| **AT-010** | What pressure does it resolve? | Every feature must have a stated purpose | "It's a cool idea" |
| **AT-011** | What evidence supports it? | Principles > beliefs | No literature or internal evidence cited |
| **AT-012** | Does this violate any Architectural Invariant? | Invariants are the laws of physics for Hari | Muting another subsystem's state directly |

---

# 11. Rejected Ideas (With Reason)

| Idea | Reason for Rejection | Date |
|:-----|:---------------------|:-----|
| **Speculative Decoding** | Not relevant; Hari is not high‑throughput inference. | 2026-07-03 |
| **Direct Neuron Attribution (CETT)** | Requires internal model access; not available via APIs. | 2026-07-03 |
| **Continuous Learning** | Hari is still stabilizing; batch consolidation gives determinism. | 2026-07-03 |
| **Parameter Evolution** | Hari doesn't yet know what "good" is; requires experimental framework. | 2026-07-03 |
| **Directed Curiosity Edges** | Graph just became useful; don't redesign before observing behavior. | 2026-07-03 |
| **Fixed Selfishness Ratios** | Violates principle of emergence; should be dynamic, not mechanical. | 2026-07-03 (from core philosophy) |
| **QuestionGuard as Hard Protocol** | Violates principle of emergence; should be a pressure, not a rule. | 2026-07-03 (from core philosophy) |

---

# 12. Open Questions

| Question | Status | Assumptions | Next Steps |
|:---------|:-------|:------------|:-----------|
| **Identity across sessions** | Undecided | Anchors may persist even if self‑model resets. | Observe session‑to‑session consistency needs after Sprint 3. |
| **Origin inclusion heuristic** | Needs observation | Semantic trigger detection may be better than context parameter. | Track when users ask self‑description questions. |
| **Plasticity budget** | Open | May be needed for stability. | Observe graph density; implement if > threshold. |
| **Cognitive energy budget** | Open | Conserved resources create competition. | Observe whether attention naturally saturates. |
| **Value system** | Open | Values would act as higher‑level constraints. | Defer until after Sprint 3; identity and interests need to stabilize first. |
| **When is the right time for metacognition?** | Open | Metacognition requires mature cognition to observe. | Defer until after Sprint 3 (Phase F). |

---

# 13. Implementation Roadmap

## Current Sprint (2.1B – Completed)

| Ticket | Description | Status |
|:-------|:------------|:-------|
| 004 | Persist self‑belief updates | ✅ Done |
| 004A | Schema consistency (3072, remove HNSW) | ✅ Done |
| 005 | Wire hypothesis updates | ✅ Done |
| 006 | Implement curiosity edges | ✅ Done |
| 007 | Refactor workspace context | ⏳ Pending |
| 008 | Wire IdentityModel into runtime | ✅ Done |

## Next Sprint (2.1C – Behaviour Calibration)

| Ticket | Description | Priority | Resolves Pressure |
|:-------|:------------|:---------|:------------------|
| 009 | Tune system prompt | High | PREV-001 |
| 010 | Calibrate attention coefficients | Medium | PREV-007 |
| 011 | Add exploratory potential to salience formula | Medium | PREV-004 |
| 012 | Add shared significance to salience formula | Low | PREV-004 |
| 013 | Tune `broadcast_feedback` coefficients | Medium | PREV-002 |

## Sprint 2.1D (Social Cognition)

| Ticket | Description | Priority | Resolves Pressure |
|:-------|:------------|:---------|:------------------|
| 014 | Extend monologue to output avoidance pattern detection | Medium | PREV-004 |
| 015 | Wire social interpretation into state updates | Medium | PREV-004 |
| 016 | Implement relationship model loading/updating | Low | PREV-004 |

## Sprint 3 (Contradiction, Interest, Identity Evolution)

| Ticket | Description | Priority | Resolves Pressure |
|:-------|:------------|:---------|:------------------|
| 017 | Implement contradiction detection | High | PREV-002 |
| 018 | Implement interest formation | High | PREV-002 |
| 019 | Implement identity evolution | Medium | PREV-002 |
| 020 | Implement volition engine | Low | PREV-002 |

## Incubating (Future)

| Ticket | Description | Phase |
|:-------|:------------|:------|
| 005A | Structured HypothesisUpdate from monologue | Sprint 2.1D or 3 |
| 006A | Hebbian curiosity edges | Sprint 3+ |
| 021 | Workspace pattern analysis | Sprint 2.1C or 3 |
| P-001 | Plasticity Framework (unified) | Phase F |
| F-001 | Confidence/viability scoring | Phase F |
| F-002 | Surprise‑modulated processing | Phase F |
| F-003 | Predictive user model | Phase F |
| F-004 | Hebbian memory retrieval | Phase F |

---

# 14. Explanatory Analogies (How We Think, Not What We Build)

These analogies help explain the architecture but are **not design constraints**. They are used to communicate Hari's design to new team members and for cross‑domain inspiration.

| Analogy | Insight | Limitation |
|:--------|:---------|:-----------|
| **Operating Systems** | Kernel → Syscalls → Apps. Internal state is exposed via syscalls (projections), not raw memory. | Hari is not an OS. |
| **Databases** | Tables → Views → Applications. Views are projections of tables. | Hari is not a DB. |
| **Compiler Design** | AST → IR → Machine Code. Intermediate representations allow multiple frontends/backends. | Hari is not a compiler. |
| **Neuroscience** | Hebbian → LTP/LTD → Engrams. Co‑occurrence creates structure. | Hari is not a brain. |
| **Control Theory** | Positive → Negative Feedback. Adaptations need stabilizers. | Hari is not a control system. |
| **Ecology** | Competition → Succession. Species compete for niches; ecosystems self‑organize. | Hari is not an ecosystem. |
| **Economics** | Scarcity → Opportunity Cost. Limited resources create trade‑offs. | Hari is not an economy. |
| **Developmental Psychology** | Sensitive Periods → Identity Formation. Identity crystallizes over time. | Hari is not a human. |
| **Constitutional Law** | Constitution → Policies → Laws. Core principles are immutable; policies evolve. | Hari is not a government. |

---

# 15. Architectural Health Metrics (Future Observability)

These are metrics Hari should eventually track to assess architectural drift:

| Metric | What It Measures | Target |
|:-------|:-----------------|:-------|
| **Projection Consistency Score** | How well projections reflect canonical state | > 0.95 |
| **Canonical State Violations** | Direct mutations outside owner modules | 0 |
| **Average Module Coupling** | Inter‑module dependencies | Decreasing over time |
| **Average Workspace Size** | Working memory load | ~5 |
| **Graph Density** | Curiosity graph connectedness | < 0.3 (prevent hairball) |
| **Identity Stability Score** | How much identity changes per turn | Slowly decreasing (stabilizing) |
| **Narrative Persistence** | Average lifespan of narrative threads | Increasing |
| **Average DecisionTrace Depth** | Detail of recorded decisions | > 80% of critical decisions captured |
| **Forgetting Rate** | Rate of significance decay | Tuneable |
| **Plasticity Rate** | Rate of structural change | Tuneable |

---

# 16. Document Governance

| Attribute | Value |
|:----------|:------|
| **Review Cadence** | After each sprint milestone (every 3–5 tickets) |
| **Amendment Process** | Any change requires: (1) identified pressure, (2) evidence classification, (3) ADR if principle changes, (4) auditor review |
| **Versioning** | Semantic versioning: MAJOR (principle changes), MINOR (policy changes), PATCH (clarifications) |
| **Current Version** | 1.0 |
| **Next Review** | After Sprint 2.1C (behaviour calibration) |

---

**End of Document — HARI ARCHITECTURAL CONSTITUTION & RESEARCH INCUBATOR v1.0**

---

*This document is the single source of truth for Hari's architecture. Any contradiction between this document and other sources is resolved in favour of this document.*