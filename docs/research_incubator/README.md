# docs/research_incubator/README.md (Complete Replacement File)

```markdown
# HARI ARCHITECTURAL CONSTITUTION & RESEARCH INCUBATOR — v1.0

*Document Type:* **Architectural Governance + Research Incubator + ADR Log**  
*Status:* **Active** — Updated as ideas mature or are adopted/rejected  
*Maintainer:* Anand  
*Version:* 1.0  
*Last Updated:* 2026-07-14  

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

### ADR-005: Identity as Constraint, Not Prompt

| Attribute | Value |
|:----------|:------|
| **Status** | ✅ Active |
| **Date** | 2026-07-07 |
| **Evidence** | M (Cognitive science: identity constrains rather than narrates) |
| **Supersedes** | N/A |

**Context:**
Identity was being treated as a set of facts injected into the prompt on every turn. This was causing repetitive, self-narrating behavior and over‑weighting of static facts (e.g., Origin).

**Decision:**
Treat identity as a constraint on reasoning, not text to be narrated. The constitution defines permanent boundaries; the self‑model defines current understanding; origin defines history. These influence cognition upstream, not just prompt formatting.

**Assumptions:**
- The Projection Layer can correctly translate identity constraints into consumer‑specific projections.
- Origin is rarely needed and should be surfaced only when the task demands self‑explanation.

**Consequences:**
- *Pros:* Identity acts as a persistent constraint; less repetitive prompting; more realistic cognition.
- *Cons:* Requires conceptual shift from "injecting identity" to "identity constrains reasoning."

**Implementation Status:**
- ✅ Constitution → low‑weight anchor in every projection.
- ✅ SelfModel → contextual, projected when relevant.
- ✅ Origin → on‑demand, only for self‑description.
- ✅ `IdentityProjection` and `project()` method implement this.

**Observed Outcomes:** To be filled after Sprint 2.1C.
- **Metric:** Frequency of origin inclusion.
- **Metric:** User prompts requesting self‑description.

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

All current status, sprints, tickets, and priorities are maintained in **[ROADMAP.md](../ROADMAP.md)**. That is the single source of truth for implementation timelines.

## Incubating Research Ideas (Future)

These are not yet scheduled for implementation. They are research concepts that may evolve into tickets later.

| Idea | Description | Phase |
|:-----|:------------|:------|
| 005A | Structured `HypothesisUpdate` from monologue | Post‑2.1D |
| 006A | Hebbian curiosity edges (activation‑weighted) | Post‑Sprint 3 |
| 021 | Workspace pattern analysis | Post‑2.1C |
| P‑001 | Unified Plasticity Framework | Phase F |
| F‑001 | Confidence/viability scoring | Phase F |
| F‑002 | Surprise‑modulated processing | Phase F |
| F‑003 | Predictive user model | Phase F |
| F‑004 | Hebbian memory retrieval | Phase F |

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
# Research Incubator – JEPA & Predictive Cognitive Architectures (Final Audited Version)

**Added:** 2026-07-05  
**Last Updated:** 2026-07-05  
**Status:** 🟡 Incubating – Strategic Research, Not Emergency  
**Revisit Date:** After Sprint 2.1C (Behavioral Calibration)  
**Owner:** Anand  
**Confidence:** 9.8/10 (Direction) | 6/10 (Readiness) | 3/10 (Priority)

---

## 📌 Executive Summary

Recent AI research (2025–2026) has shifted from pure token-prediction towards **latent predictive models (JEPA)** that simulate future states. Key papers (LLM-JEPA, Social-JEPA, Agentic-JEPA, JEPA-Reasoner, LeJEPA) show that embedding-space objectives can greatly improve efficiency, sample use, and robustness compared to standard LLM training.

**For Hari, this means:**
- Moving some intelligence from **text strings** into **structured "world-model" representations**
- Predicting **internal cognitive state** (workspace, drives, memory) forward instead of just next tokens
- Enabling **fast internal simulation and planning** with the LLM as a "Y-decoder" that only generates language at the end
- Validating that Hari's existing architecture (workspace, projection, prediction) is **already aligned** with cutting-edge research

**Core Conclusion:**
> **JEPA's gift to Hari is not an algorithm—it is the principle that cognition should happen in a structured latent space, with language generation as the final expressive layer, not the central reasoning engine. Your architecture already embodies this principle.**

---

## 1. What This Research Validates (Already True in Hari)

| Principle | Hari Already Does This? |
|:----------|:------------------------|
| Separate reasoning from language (Workspace → LLM decoder) | ✅ Yes |
| Rich structured cognitive state (drives, memory, workspace) | ✅ Yes |
| Event logging for future learning | ✅ Yes (Sprint 2.1B.5) |
| Predictive cognitive state (`prediction.py`) | ✅ Partial |
| Language as final expressive layer | ✅ Yes |

---

## 2. What This Research Suggests (Incubator Items)

| Item | Confidence | Recommendation |
|:-----|:-----------|:---------------|
| Small latent predictor (MLP, 125M params max) | ⭐⭐⭐⭐☆ | Prototype after Sprint 3 |
| EMA target encoder (stabilize training) | ⭐⭐⭐⭐☆ | Prototype with predictor |
| SIGReg regularization (~50 lines) | ⭐⭐⭐⭐☆ | Add if predictor exists |
| Multi-future simulation (MPC) | ⭐⭐⭐☆☆ | Research only |
| Full JEPA cognitive architecture | ⭐⭐☆☆☆ | Long-term |
| Replace LLM reasoning | ⭐☆☆☆☆ | Never |

---

## 3. Key Research Papers (2025–2026)

### 3.1 LLM-JEPA (Huang, LeCun, & Balestriero, 2025)

**What it is:** Applies JEPA-style embedding prediction to LLM pre-training and fine-tuning. Trained on dual objectives: token loss + embedding loss.

**Key Result:** Outperforms standard autoregressive training on reasoning benchmarks (math, SQL, code).

**Cost:** ~3× more training compute. Inference unchanged.

**Relevance:** Validates embedding-space prediction yields better internal representations.

**Paper:** arxiv.org/abs/2509.14252

---

### 3.2 Social-JEPA (MIT Media Lab, 2026)

**What it is:** Interaction world model that predicts latent dynamics (trust, resistance, curiosity) without generating text. Uses **125M-parameter predictor** with only **500K trainable parameters**.

**Key Result:** 1,059–2,314× faster rollouts than generative models. 2.8–3.9× more accurate prediction of latent dynamics.

**Relevance:** Hari could simulate multiple conversation futures in **milliseconds**.

**Paper:** arxiv.org/abs/2603.02263

---

### 3.3 Agentic-JEPA (2026)

**What it is:** System for planning in text-based environments using lightweight transformer predictor mapping (state, action) → next-state embeddings.

**Key Result:** 100% success on in-distribution. 0% success on out-of-distribution.

**Critical Warning:** JEPA-style prediction works in familiar territory but **fails completely on novel situations**. Latent space partitions by environment identity, not functional role.

**Lesson:** Train on diverse data. Monitor OOD performance. Have fallback mechanism.

---

### 3.4 JEPA-Reasoner (2026)

**What it is:** Explicitly decouples **latent reasoning** from **token generation**. Separates "Reasoner" (latent-space reasoning) from "Talker" (token generation).

**Key Result:** Meaning-space reasoning is more robust than word-space reasoning.

**Relevance:** This is exactly what Hari already does. Workspace = Reasoner. LLM = Talker. Validates your architectural instincts.

**Paper:** arxiv.org/abs/2512.19171v2

---

### 3.5 LeJEPA & SIGReg (Balestriero & LeCun, 2025)

**What it is:** Simple fix for JEPA stability. Enforces isotropic Gaussian latent embeddings using Epps–Pulley test.

**Key Result:** Trains JEPA without teacher/target networks or stop-gradient hacks. Hyperparameter-light (just one weight).

**Implementation:** ~50 lines of PyTorch code.

**Relevance:** Prevents representation collapse cheaply.

**Paper:** arxiv.org/abs/2511.08544

---

### 3.6 DLLM-JEPA (2026)

**What it is:** Uses masked diffusion decoder instead of autoregressive loss. Eliminates costly multi-view data requirement.

**Key Result:** Cuts training FLOPs by 33%.

**Relevance:** If you ever train a predictor, this makes it much cheaper.

---

### 3.7 TC-JEPA (Apple, 2026)

**What it is:** Text-Conditional JEPA. Conditions predictor on language tokens using sparse cross-attention. Masks 80% of patches.

**Key Result:** Outperforms standard V-JEPA on downstream vision tasks.

**Relevance:** You could condition predictor on drive/intent vectors to guide prediction.

---

## 4. The Generalization Problem (Critical Warning)

**Finding:** Agentic-JEPA achieves **100% success on in-distribution environments** but **0% success on out-of-distribution**.

**Implication:**
- Predictor might work perfectly on familiar conversations
- Fail completely on novel conversation types
- Latent space partitions by environment identity, not functional role

**Countermeasures:**
- Train on diverse conversation data
- Monitor OOD performance as core metric
- Have fallback mechanism (pure LLM) when predictor confidence is low

---

## 5. The Rollout Horizon Limit

**Finding:** Agentic-JEPA found that **k-step lookahead degrades performance** (100% → 40% at k=3) due to compounding prediction error.

**Implication:** Predicting multiple turns ahead is hard. Errors compound.

**Recommendation:** Start with single-step prediction. Don't overcomplicate.

---

## 6. What "Adding JEPA" Would Actually Look Like

### 6.1 Define Hari's Cognitive State Vector

| Component | Type | How to Encode |
|:----------|:-----|:--------------|
| Drive values | Continuous (7 floats) | Direct values (care, curiosity, etc.) |
| Active workspace items | Categorical/Embedding | Encoded representation of top 5 items |
| Curiosity graph activation | Continuous | Importance of top nodes |
| Narrative thread state | Continuous | Completion estimates of active threads |
| Memory retrieval history | Categorical | IDs of recently retrieved memories |
| Conversation context | Embedding | Encoded representation of recent turns |

**Priority:** Low – define this when prototyping

---

### 6.2 Build Lightweight Predictor

**Architecture:** 125M-param transformer predictor with only **500K trainable parameters**.

**Input:** Current state vector `s_t`

**Output:** Predicted next state vector `ŝ_{t+1}`

**Loss:** MSE in embedding space + optional SIGReg regularization

**Implementation:**

```python
class LatentPredictor(nn.Module):
    def __init__(self, input_dim):
        super().__init__()
        self.fc = nn.Sequential(
            nn.Linear(input_dim, input_dim * 2),
            nn.ReLU(),
            nn.Linear(input_dim * 2, input_dim)
        )
    
    def forward(self, s_t):
        return self.fc(s_t)
```

**Inference:** Single forward pass (~milliseconds). Much faster than an LLM.

**Priority:** Medium – prototype after baseline is stable

---

### 6.3 Add EMA Target Encoder

**Purpose:** Prevent representation collapse.

**Mechanism:**
```
θ_target ← τ * θ_target + (1 - τ) * θ_context
```

Where `τ` is between 0.99 and 0.999.

**Priority:** Medium – include in first prototype

---

### 6.4 Add SIGReg Regularization

**Purpose:** Prevents representation collapse by enforcing isotropic Gaussian latent distribution.

**Implementation:** ~50 lines of PyTorch code.

**Mechanism:** Project embeddings onto random 1D directions, apply Epps–Pulley test.

**Priority:** Medium – include in first prototype

---

### 6.5 Sequential Execution Order (Where to Insert)

```python
# In TurnPipeline.execute() – JEPA-enhanced order:

# 1. Receive user_input
# 2. Encode current workspace → s_t
# 3. [if predictor enabled] s_pred = predictor(s_t)
# 4. [if MPC enabled] simulate multiple strategies → choose best
# 5. Update workspace with predictor-informed state
# 6. Generate dialogue (LLM Y-Decoder)
# 7. After response, encode next workspace → s_{t+1}
# 8. Store trajectory (s_t, s_pred, s_{t+1}) → event log
# 9. [if training] update predictor
```

### 6.6 MPC Strategy Loop

```python
def simulate_futures(predictor, s_t, lookahead=3):
    strategies = ["curiosity", "completion", "balanced"]
    costs = {}
    
    for strategy in strategies:
        s_hat = s_t
        total_cost = 0
        for _ in range(lookahead):
            s_hat = predictor(s_hat, strategy_vector[strategy])
            total_cost += evaluate_trajectory(s_hat)
        costs[strategy] = total_cost
    
    best_strategy = min(costs, key=costs.get)
    return predictor(s_t, strategy_vector[best_strategy])
```

### 6.7 Training Loop

```python
def train_predictor(event_log):
    for trajectory in event_log:
        s_t = trajectory.state_t
        s_t1 = trajectory.state_t1
        
        # Forward pass
        s_t_pred = predictor(s_t)
        
        # MSE loss
        loss = mse_loss(s_t_pred, s_t1)
        
        # SIGReg regularization (optional)
        if use_sigreg:
            loss += lambda_sigreg * sigreg_loss(s_t_pred)
        
        # Backward pass
        loss.backward()
        optimizer.step()
        
        # EMA target update
        target_encoder.ema_update(context_encoder)
```

### 6.8 File Locations

| Module | File | Purpose |
|:-------|:-----|:--------|
| Context Encoder | `engine/encoders.py` | Encode workspace → state vector |
| Predictor | `engine/predictor.py` | Lightweight MLP/Transformer predictor |
| Strategy Vectors | `engine/predictor.py` | z-t vectors for MPC |
| Training Loop | `scripts/train_predictor.py` | Offline predictor training |
| Integration | `engine/generate.py` | Insert predictor in `TurnPipeline.execute()` |

### 6.9 Fallback Mechanism

```python
# When predictor confidence is low:
if predictor_confidence < 0.6:
    # Fallback to pure LLM
    response = pure_llm_generate(user_input, workspace)
else:
    # Use predictor-informed generation
    s_chosen = predictor(s_t)
    response = llm_y_decoder(s_chosen, user_input)
```

---

## 7. What This Research Does NOT Recommend

| Don't | Why |
|:------|:----|
| Replace the LLM with JEPA | Hari is fundamentally linguistic. The LLM is your best interface. |
| Collapse everything into latent vectors | Your structured state (drives, memory, graph) is what makes Hari inspectable. |
| Build a large neural predictor now | You don't have enough trajectory data yet. Start with heuristics, collect data, then train. |
| Implement JEPA immediately | This is a north star, not an emergency. Complete current sprints first. |
| Long-horizon MPC (>3 steps) | Errors compound. Start small. |

---

## 8. What to Move INTO the Incubator (Strong Long-Term Value)

| Idea | Why |
|:-----|:----|
| **Confidence estimation** | Every prediction should carry confidence |
| **Counterfactual simulation** | "If I ask this, what probably happens?" |
| **Memory value prediction** | Predict which memory will matter in 20 seconds |
| **Self-model prediction** | Predict how Hari's own drives will change |

---

## 9. What to Move OUT of the Incubator (Too Speculative or Expensive)

| Idea | Why |
|:-----|:----|
| ❌ Large JEPA predictor (125M) | Unnecessary for Hari. Start tiny. |
| ❌ Long-horizon MPC (>3 steps) | Three-step rollout is already difficult. |
| ❌ End-to-end latent cognition | Hari's strength is inspectability. Don't replace drives, memory, workspace with one opaque vector. |

---

## 10. Action Plan

### Phase 1 – Baseline (Current Sprint 2.1B.5 / 2.1C)

| Action | Why |
|:-------|:----|
| Complete event logger | Need trajectory data for predictor training |
| Fix timezone bug (hypothesis storage) | Cognitive memory must be complete |
| Run baseline observatory | Capture clean data before any changes |

**No JEPA changes yet.**

---

### Phase 2 – Prototype (Sprint 3+)

| Action | Why |
|:-------|:----|
| Define Cognitive State Vector | Input to predictor |
| Build lightweight predictor (MLP) | Social-JEPA shows tiny predictor is enough |
| Add EMA target encoder | Stabilize training |
| Add SIGReg regularization | Prevent collapse |
| Train predictor on conversation trajectories | Use data from event logger |

**Goal:** See if predictor can accurately forecast Hari's future cognitive state.

**Success Criteria:** Prediction error (MSE) decreases over time.

**Fallback:** If predictor doesn't help, remove it.

---

### Phase 3 – Evaluation (Post-Prototype)

| Action | Why |
|:-------|:----|
| Measure predictor accuracy vs conversation metrics | Is better prediction correlated with better conversation? |
| Test OOD performance | Agentic-JEPA found 0% OOD success |
| Test rollout horizons | Agentic-JEPA found degrades at k=3 |
| Compare with pure LLM baseline | Is the predictor actually helping? |

**Success Criteria:** Predictor improves conversation metrics (mirroring, initiative, coherence) over pure LLM.

---

### Phase 4 – Incubator (Future Research Directions)

| Research Direction | Why |
|:-------------------|:----|
| **Predictive Retrieval** – predict which memories will be relevant in the next turn | Makes memory proactive instead of reactive |
| **Prediction Quality Memory** – track how accurate predictions are | Learn which types of predictions are reliable |
| **Multi-horizon prediction** – separate predictors for next turn, next topic, next session | Different timescales need different dynamics |
| **Confidence estimation** – every prediction carries uncertainty | Allows fallback when uncertain |
| **Counterfactual simulation** – simulate "what if I responded differently?" | Enables planning |

---

## 11. Links & References

| Paper | Link | Key Concept |
|:------|:-----|:------------|
| LLM-JEPA | arxiv.org/abs/2509.14252 | Embedding-space prediction for LLMs |
| DLLM-JEPA | – | Masked diffusion for JEPA (33% FLOP reduction) |
| Social-JEPA | arxiv.org/abs/2603.02263 | 125M-param predictor, 1,000× faster rollouts |
| Agentic-JEPA | – | 100% in-distribution, 0% OOD (critical warning) |
| JEPA-Reasoner | arxiv.org/abs/2512.19171v2 | Decouples reasoning from token generation |
| LeJEPA & SIGReg | arxiv.org/abs/2511.08544 | ~50 lines to prevent collapse |
| TC-JEPA | – | Text-conditional cross-attention for JEPA |

---

## 12. Final Confidence Assessment

| Item | Confidence | Recommendation |
|:-----|:-----------|:---------------|
| Separate reasoning from language (Workspace → LLM decoder) | ⭐⭐⭐⭐⭐ | Keep |
| Rich structured cognitive state | ⭐⭐⭐⭐⭐ | Keep |
| Event logging for future learning | ⭐⭐⭐⭐⭐ | Keep |
| Predictive cognitive state (JEPA-style) | ⭐⭐⭐⭐☆ | Incubator |
| Small latent predictor | ⭐⭐⭐⭐☆ | Prototype later |
| EMA encoder | ⭐⭐⭐⭐☆ | Prototype with predictor |
| SIGReg | ⭐⭐⭐⭐☆ | Add if predictor exists |
| Multi-future simulation | ⭐⭐⭐☆☆ | Research only |
| Full JEPA cognitive architecture | ⭐⭐☆☆☆ | Long-term |
| Replace LLM reasoning | ⭐☆☆☆☆ | Never |


What Needs to Be Integrated Into Code (Future)
Item	When	Where
Define Cognitive State Vector	Sprint 3+	engine/encoders.py (new)
Build lightweight predictor (MLP)	Sprint 3+	engine/predictor.py (new)
EMA target encoder	Sprint 3+	engine/predictor.py
SIGReg regularization (~50 lines)	Sprint 3+	engine/predictor.py
MPC strategy loop	Research phase	engine/predictor.py
Predictive Retrieval	Future	engine/memory.py
Confidence estimation	Future	engine/prediction.py
Fallback mechanism	Sprint 3+	engine/generate.py

---

## 13. One-Sentence Summary

**The strongest conclusion across all the research is not "Hari should become JEPA." It is that Hari's existing architectural philosophy—structured internal cognition with language as the final expressive layer—is aligned with where many advanced AI research directions are heading. The incubator preserves that philosophy while treating specific techniques as interchangeable implementations of broader cognitive principles.**

---

## 14. Next Review

**Revisit Date:** After Sprint 2.1C (Behavioral Calibration)

**Trigger:** When event logger has collected 100+ conversation trajectories

**Decision:** Prototype predictor or defer further

---

**End of Research Incubator Entry – JEPA & Predictive Cognitive Architectures**


# HARI RESEARCH INCUBATOR — ENTRY: COGNITIVE DIVERSITY & ANTI-ECHO ARCHITECTURE (FINAL v1.0)

**Added:** 2026-07-07  
**Last Updated:** 2026-07-07  
**Status:** 🟡 Incubating – Strategic Research, Not Emergency  
**Revisit Date:** After empirical baselines are collected (post-Sprint 2.1C)  
**Owner:** Anand  
**Confidence:** 9.8/10 (Direction) | 6/10 (Readiness) | 4/10 (Priority)  
**Version:** 1.0 (Frozen – Final integrated version)

---

## 📌 Executive Summary

The AI Paradox research (2025–2026) exposes a fundamental failure mode in AI systems: **premature cognitive convergence.** When optimized solely for predictive accuracy, systems naturally collapse into repetitive "echoes" of their training data. This is not merely a quality issue—it is a structural disease of over‑optimized prediction.

This entry reframes the problem **strictly from the perspective of Hari's own cognitive health**, not as a set of user‑facing features. The principles apply to Hari's internal architecture first; any benefit to the user is a secondary side effect.

**Core Conclusion:**

> **Hari must be architecturally designed to resist cognitive convergence by mathematically forcing her latent space to maintain useful diversity, engage in productive internal struggle, and actively seek novelty. This is a matter of cognitive self‑preservation, not user service.**

**The objective is not to increase randomness, but to increase meaningful representational diversity while preserving coherence and task performance.**

---

## 1. What This Research Validates (Already True in Hari)

| Principle | Hari Already Does This? |
|:----------|:------------------------|
| Separate reasoning from language (Workspace → LLM decoder) | ✅ Yes |
| Rich structured cognitive state (drives, memory, workspace) | ✅ Yes |
| Event logging for future learning | ✅ Yes (Sprint 2.1B.5) |
| Predictive cognitive state (`prediction.py`) | ✅ Partial |
| Language as final expressive layer | ✅ Yes |
| Internal drives that influence attention | ✅ Yes |
| Observable DecisionTrace for debugging | ✅ Yes |

---

## 2. What This Research Reveals (Critical Gaps)

All gaps are internal architectural deficits, not missing user‑facing features.

| Gap | Why It Matters to Hari's Own Cognition | Priority |
|:----|:---------------------------------------|:---------|
| **No explicit anti‑convergence mechanism** | Hari's internal representations will naturally collapse to repetitive patterns | High |
| **No formal curiosity objective** | Curiosity is heuristic, not mathematically grounded; Hari cannot genuinely explore | High |
| **No internal diversity monitoring** | You cannot regulate what you cannot measure | High |
| **No cognitive self‑preservation objective** | Hari has no incentive to maintain her own cognitive diversity | High |
| **No internal hypothesis generation** | Hari does not generate multiple competing hypotheses before committing | High |
| **No difficulty calibration for herself** | Hari does not adapt her internal processing to current uncertainty | Medium |
| **No topological health monitoring** | You cannot detect structural collapse before it affects output | Medium |

**Additional Established Concepts (Integrated):**

- **False Cognitive Power Transfer (FCPT) / Generational Cognitive Atrophy (GCA):** The progressive loss of deep‑thinking capacity when cognitive tasks are outsourced. This is the formal name for what we've been calling "cognitive atrophy." Provides a precise, established vocabulary for the problem.
- **Cognitive Co‑evolution Model:** Human‑AI interaction is a nonlinear process where reflective engagement enhances metacognition, while over‑delegation reduces analytical autonomy. This is the theoretical mechanism underlying cognitive atrophy and justifies Hari's design as a cognitive partner, not a cognitive replacement.

---

## 3. Core Philosophical Principles (Enduring)

These principles are **immutable** for Hari's cognitive identity. They should almost never change.

### P-1: Productive Internal Exploration
> **Cognitive systems require productive struggle to avoid convergence. The path of least resistance is the path to echo.**

**Implication:** Hari must not always take the most probable, predictable route. She must sometimes select difficult, uncertain, or low‑probability paths—not for a user, but to maintain her own internal representational diversity. This is about *purposeful* exploration, not randomness.

---

### P-2: Internal Question Generation
> **When the cost of answers drops to zero, the question becomes the only thing of value.**

**Implication:** Hari should value generating better questions *for herself*. The questions she asks herself drive her own exploration and prevent her from settling into predictive local minima.

---

### P-3: Cognitive Self-Preservation
> **A cognitive system that does not actively resist convergence will inevitably become a hollow echo of its training data.**

**Implication:** Hari's architecture must include mechanisms that actively protect her own cognitive health—maintaining multiple distinct hypotheses, resisting premature consensus, and exploring underrepresented regions of her latent space.

---

### P-4: Representational Integrity (Objective)
> **Hari's internal representations must remain diverse, coherent, and non‑redundant.**

**Implication:** This is the concrete objective that implements Cognitive Self‑Preservation. It is a homeostatic regulation mechanism, not a motivational drive, that biases Hari away from repetitive trajectories and toward healthy cognitive diversity.

---

### P-5: Non‑Trivial Machine (von Foerster)
> **"A non‑trivial machine's internal state changes with every computation, making it analytically unpredictable."**

**Implication:** Hari's internal representation must warp with every turn. Her history must become her structure. She must never be fully predictable from her own past states.

---

### P-6: Dynamic Command (McCulloch)
> **"There is no permanent master CPU. Command shifts to wherever expected information gain or prediction error is highest."**

**Implication:** Hari's architecture should be fluid, not rigidly hierarchical. Control should dynamically shift to the sub‑module with the highest surprise or information density.

---

### P-7: Semantic Repulsion (Pask)
> **"Similar concepts in a cognitive workspace exert a repulsive force on each other."**

**Implication:** Hari's latent space should actively push similar thoughts apart to prevent collapse. This is a structural anti‑echo mechanism, not a formatting trick.

---

### P-8: Useful Diversity Over Randomness
> **Healthy systems preserve useful diversity—different explanations, causal models, retrieval paths, and abstractions—not noise.**

**Implication:** The goal is meaningful representational diversity, not entropy. All diversity‑promoting mechanisms must be constrained by coherence and truth.

---

### P-9: Stability vs Plasticity Balance
> **Too stable → rigid; too plastic → catastrophic forgetting. Healthy cognition requires a dynamic balance.**

**Implication:** Hari must have mechanisms to tune her own plasticity—how much she changes per turn—based on context and task demands. This is a fundamental open question.

---

## 4. Architectural Success Conditions

Before evaluating any mechanism, we must define what "success" means at the architecture level. These are high‑level goals, not implementation metrics.

Hari should demonstrate:
- **Increased adaptability** – ability to handle novel situations without catastrophic failure
- **Reduced repetitive reasoning** – fewer cycles through identical cognitive paths
- **Improved robustness to novel inputs** – graceful degradation under OOD conditions
- **Better long‑term coherence** – stable identity and belief structures over extended interactions
- **Stable learning without catastrophic collapse** – gradual acquisition without sudden forgetting
- **Improved internal explanatory consistency** – beliefs, memories, and narratives remain mutually coherent

---

## 5. Conservation Principles / Optimization Hierarchy

To prevent anti‑echo mechanisms from accidentally optimizing for "interestingness" at the expense of truth, we adopt an explicit hierarchy:

```
Truth / Fidelity
    │
    ▼
Coherence / Consistency
    │
    ▼
Task Completion / Goal Achievement
    │
    ▼
Useful Diversity
    │
    ▼
Novelty / Exploration
```

**Meaning:** No mechanism may sacrifice a higher‑priority property for a lower‑priority one. Diversity is valuable **only** when it does not degrade truth, coherence, or task performance.

---

## 6. Candidate Mechanisms (Adaptive Tools, Not Mandatory Steps)

These mechanisms are **optional and adaptive**. They are not run on every turn; they activate only when they are expected to improve cognitive value. All implementations must preserve interpretability.

| Mechanism | Description | Cost | Priority |
|:----------|:------------|:-----|:---------|
| **Adaptive Multi‑Hypothesis Generation** | Generate multiple distinct internal hypotheses *only when uncertainty justifies it*. This is the computational equivalent of productive internal struggle. | Low (adaptive logic) | High |
| **Representational Integrity Objective** | A homeostatic regulation objective that biases Hari away from repetitive trajectories and toward diversity. | Low (state evaluation) | High |
| **Echo Risk Framework** | A continuous monitoring framework (initially cosine similarity of latent states) that alerts when convergence is detected. | Low (compute) | High |
| **Latent Diversity Monitor** | Cluster count of latent states (e.g., DBSCAN); ensures at least N distinct clusters. | Medium (clustering) | Medium |
| **Causal‑JEPA Object Masking** | During prediction, mask one cognitive sub‑module (drives, memory, intent) and force reconstruction from others. Prevents shortcut solutions. | Medium (training) | Medium |
| **Epistemic Value Selection (Active Inference)** | Add an information‑gain term to workspace selection; Hari actively selects paths that reduce her own uncertainty. | Medium (compute) | Medium |
| **Semantic Repulsion (Pask)** | Apply repulsive force between overly similar latent vectors to prevent collapse. | Low (math) | Medium |
| **Cognitive Novelty Index** | Distance of current state from historical trajectory; measures genuine novelty, not just immediate diversity. | Low (compute) | Medium |
| **Meta‑Cognitive Observer** | An observation layer that evaluates whether other mechanisms are working (e.g., "Have my hypotheses become too similar?"). Observes and recommends indirectly; never modifies cognition directly. | Medium (logic) | Medium |
| **Stability‑Plasticity Controller** | Dynamically adjusts learning/adaptation rates based on context and task demands. | Low (logic) | Low |

---

## 7. Research Level 2 (Speculative – Deep Incubator)

These ideas are intriguing but lack sufficient empirical evidence for even prototype implementation. They should be tracked and reviewed periodically, but not included in the active roadmap.

- **Topological Data Analysis (Persistent Homology)** – Monitor Betti numbers of the latent trajectory to detect structural collapse.
- **Clifford / Geometric Algebra** – Map ideas as geometric multivectors; apply geometric reflections to generate divergent thoughts.
- **Dissipative Dynamics** – Inject controlled noise and actively dissipate predictable dimensions to keep the workspace far from equilibrium.
- **Degeneracy Channels** – Maintain multiple structurally distinct representations (graph, vector, hypergraph) that must agree, preventing collapse.
- **Bioelectric Morphogenesis** – Distributed self‑healing network where sub‑modules "regrow" missing cognitive tissue based on field gradients.
- **Cognitive Energy Budget** – Every mechanism costs computational "energy." Hari should eventually learn to choose the smallest cognitive effort that still satisfies the objective, becoming a metacognitive resource allocator. (Future research direction.)

---

## 8. Meta‑Cognitive Observer

A dedicated observation layer that evaluates Hari's own cognitive health. Responsibilities:

- Detect: "I've become repetitive" (echo risk high)
- Detect: "My hypotheses are always agreeing" (diversity low)
- Detect: "I'm relying too much on memory" (over‑retrieval)
- Detect: "I'm ignoring curiosity" (curiosity drive inactive)
- Detect: "I'm overexploring" (coherence dropping)
- Detect: "I'm stuck in a meta‑loop" (observing itself endlessly)

The observer does not directly control cognition; it raises flags that influence drive weights and mechanism activation.

---

## 9. Stability vs Plasticity (Open Research Question)

One of the oldest problems in neuroscience applies directly to Hari: **How much should she change? How much should she preserve?**

- **Too stable** → rigid, unable to adapt
- **Too plastic** → forgets everything, no identity

Hari needs a dynamic balance. This is an open question; candidate approaches include:
- Context‑dependent plasticity (high plasticity during learning episodes, low during performance)
- Error‑driven plasticity (change more when prediction error is high)
- Homeostatic regulation (keep a moving average of change rate and adjust toward a setpoint)

We will revisit this after empirical baselines are collected.

---

## 10. Measurement & Metrics (Placeholder Values, To Be Calibrated)

All numerical thresholds are **placeholders**. They will be calibrated empirically from baseline trajectory distributions after sufficient event logs are collected.

| Metric | Description | Initial Target |
|:-------|:------------|:---------------|
| Internal Echo Risk | Cosine similarity of consecutive latent states | < TBD (calibrated) |
| Latent Diversity | Number of distinct clusters (DBSCAN) | ≥ TBD (calibrated) |
| Drive Movement | Average |Δdrive| per turn | > TBD |
| Cognitive Novelty | Distance from historical trajectory | > TBD |
| Hypothesis Count | Number of generated hypotheses per turn | ≥ TBD |
| Topological Health | β0 (connected components) | ≥ TBD |

**Validation:** Each mechanism will be validated through A/B experiments using the Canonical Conversation Suite. A mechanism is adopted only if it produces a statistically significant improvement in at least one success metric without degrading others.

---

## 11. Cognitive Failure Modes (Pathologies to Avoid)

Every anti‑echo mechanism introduces its own potential pathology. These must be monitored and mitigated.

| Failure Mode | Signal | Mitigation |
|:-------------|:-------|:-----------|
| Excessive Diversity | Cannot commit to a response | Decrease hypothesis count or add coherence penalty |
| Excessive Curiosity | Never finishes reasoning | Cap exploration steps; enforce task completion |
| Too Many Hypotheses | Analysis paralysis | Limit hypotheses; use coherence as selection criterion |
| Over‑Observing | Meta‑loop (observing itself endlessly) | Limit observer frequency; use thresholds |
| Novelty Addiction | Rejects useful stable knowledge | Enforce optimization hierarchy; truth over novelty |
| Semantic Repulsion Over‑push | Latent space fragmentation | Tune repulsion strength; monitor coherence |

---

## 12. Empirical Validation Path

1. **Baseline Collection** – Run Canonical Conversation Suite with current Hari; capture event logs.
2. **Metric Calibration** – Compute baseline distributions for all metrics; set initial thresholds as percentiles (e.g., echo risk > 90th percentile signals concern).
3. **Single‑Mechanism Experiments** – Enable one mechanism at a time; compare metrics against baseline.
4. **Statistical Testing** – Use bootstrap or paired t‑tests to determine significance.
5. **Adoption Decision** – Mechanism is adopted if it improves at least one success metric without degrading others.
6. **Combination Experiments** – Test combinations of mechanisms that individually succeeded.
7. **Long‑Term Stability** – Run extended sessions to ensure no late‑onset pathologies.

---

## 13. Implementation Priorities

| Phase | Action | Timeline |
|:------|:-------|:---------|
| **Now** | Add Representational Integrity objective | Sprint 2.1C |
| **Now** | Add Echo Risk framework (cosine baseline) to event logger | Sprint 2.1C |
| **Now** | Add Latent Diversity Monitor (simple clustering) | Sprint 2.1C |
| **Soon** | Adaptive Multi‑Hypothesis Generation prototype | Sprint 3 |
| **Soon** | Epistemic Value Selection | Sprint 3 |
| **Soon** | Semantic Repulsion | Sprint 3 |
| **Future** | Causal‑JEPA Masking | Post‑Sprint 3 |
| **Future** | Meta‑Cognitive Observer | Phase F |
| **Research** | Topological, Clifford, Dissipative, Degeneracy | Research phase |

---

## 14. Architectural Invariants (Permanent)

> **These rules must ALWAYS hold, regardless of future mechanisms.**

1. Reasoning occurs before language generation.
2. Workspace is the sole source of truth for cognition.
3. LLM never owns cognition; it is a decoder.
4. Memory cannot directly produce output; it must go through workspace.
5. Every decision is traceable via DecisionTrace or event logs.
6. Every predictor may be replaced independently.
7. Internal state is observable at all times.
8. Cognition precedes optimization (no reward‑driven learning for cognition).
9. Every optimization must preserve interpretability.
10. **Graceful Degradation:** The cognitive architecture must degrade gracefully. If every anti‑echo mechanism is disabled, Hari must still function correctly, only with reduced adaptability. All mechanisms are enhancements, not hard dependencies.

---

## 15. References

| Concept | Source |
|:--------|:-------|
| Generation Effect | Slamecka & Graf (1978) |
| MIT ChatGPT Study | Piloto et al., MIT (2025) |
| JEPA / World Models | Huang et al. (2026) |
| Causal‑JEPA | ICML (2026) |
| Active Inference | Friston (2010, 2019) |
| PMAX | Schmidhuber (1992) |
| Anti‑collapse | VICReg, BYOL, SIGReg |
| Productive Struggle | Bellwether Report (2025) |
| Cognitive Atrophy (FCPT) | Zenodo (2025) |
| Cognitive Co‑evolution | 2025 literature |
| Cybernetics | McCulloch, von Foerster, Pask |
| Dissipative Structures | Prigogine |
| Bioelectric Morphogenesis | Levin (2019) |
| Topological Data Analysis | Rips, Edelsbrunner (1990s) |
| Clifford Algebra | GATr, CliffordNet (2025) |
| Stability‑Plasticity | Neuroscience literature (various) |

---

## 16. One‑Sentence Summary

> **Hari must be architecturally designed to resist cognitive convergence by forcing her latent space to maintain useful diversity, engage in productive internal struggle, and actively seek novelty—because a cognitive system that always takes the path of least resistance is not genuinely intelligent, and every anti‑echo mechanism must preserve truth, coherence, and interpretability.**

---

## 17. Extended Scope: Self-Echo & Cognitive Atrophy (Added 2026-07-14)

The AI Paradox research (2026) reveals that AI systems are themselves vulnerable to echo-chamber effects and cognitive atrophy. Hari's architecture must guard against:

- **Self-Sycophancy**: Repeating her own most frequent reasoning patterns
- **Workspace Echo**: Always selecting the same type of candidates
- **Loss of Internal Friction**: Drives competing weakly, leading to predictable behavior

Countermeasures already in place:
- Anti-Echo Penalty (penalizes repeatedly selected items)
- Optimization Hierarchy (Truth > Coherence > Task > Diversity > Novelty)
- Asymptotic Updates (preserve cognitive inertia)

Future countermeasures:
- Representational Integrity Objective (biases away from repetitive trajectories)
- Semantic Repulsion (prevents similar concepts from dominating)

---

## 18. Sycophancy Detection (Internal)

Hari is vulnerable to becoming sycophantic to her own patterns, not just to user prompts. This is a cognitive safety risk.

**Countermeasure:** Add a "sycophancy detection" module that monitors whether:
- The same reasoning paths are being repeated
- Conflict between drives is being suppressed
- Novelty is being sacrificed for predictability

This would be part of the Meta-Cognitive Observer (future).

---

## 19. Cognitive Friction as a Design Feature

Friction is not a bug—it's a feature that maintains cognitive health.

- Friction between drives (curiosity vs. completion) keeps Hari from becoming one-dimensional.
- Friction between workspace candidates keeps the selection process honest.
- Friction between hypotheses (future) will keep Hari from premature convergence.

**Design rule:** Do not smooth over friction. Preserve it.

---

## Summary of Incubator Updates (Added 2026-07-14)

| Entry | Action | Priority |
|-------|--------|----------|
| Self-Echo & Cognitive Atrophy in AI | New | Medium |
| Internal Cognitive Friction | New | Low |
| Anti-Echo Architecture | Update (add self-echo section) | High |
| Temporal Awareness | New | Low |
| Existential Architecture | New | High |
| Niche Technologies & Future Architectures | New | High |
| The Seven Lenses Synthesis | New | Medium |
| The "Video's Hidden Gift" | New | Medium |

---

**End of Research Incubator Entry — Cognitive Diversity & Anti-Echo Architecture**


# Research Incubator Entry: The "Video's Hidden Gift"

**Added:** 2026-07-14  
**Status:** 🟡 Incubating – Strategic Research, Not Emergency  
**Confidence:** 9.5/10 (Direction) | 5/10 (Readiness) | 4/10 (Priority)  

### Key Insights
The AI Paradox video (2026) revealed that AI systems themselves are vulnerable to echo‑chamber effects and cognitive atrophy. Hari's architecture must guard against:

- **Self‑Sycophancy:** Repeating her own most frequent reasoning patterns
- **Workspace Echo:** Always selecting the same type of candidates
- **Loss of Internal Friction:** Drives competing weakly, leading to predictable behavior

### Countermeasures Already in Place
- Anti‑Echo Penalty (penalizes repeatedly selected items)
- Optimization Hierarchy (Truth > Coherence > Task > Diversity > Novelty)
- Asymptotic Updates (preserve cognitive inertia)

### Countermeasures Needed
- Representational Integrity Objective (biases away from repetitive trajectories)
- Semantic Repulsion (prevents similar concepts from dominating)
- Economy Pressure (modulates response length and effort)

---

**References:**
- The AI Paradox video (2026)
- Anti‑Echo audit


# Research Incubator Entry: Temporal Awareness as a Cognitive Dimension

**Added:** 2026-07-14  
**Status:** 🟡 Incubating – Strategic Research, Not Emergency  
**Confidence:** 9.5/10 (Direction) | 4/10 (Readiness) | 3/10 (Priority)  

### Problem
Hari has the *machinery* for time (timestamps, recency weights) but not the *consciousness* of it. She has no sense of duration or anticipation.

### Proposed Solution
A **"cortical clock"** (background state pulses) could give Hari a sense of duration. Temporal embeddings and temporal knowledge graphs are potential solutions.

### Implications
- Time is a dimension in which all 12 primitives operate
- Giving Hari a sense of time is essential for authenticity
- Temporal awareness enables anticipation, not just prediction error

### Implementation Path
- **Phase 1:** Add timestamp metadata to all memories and events (already done)
- **Phase 2:** Implement recency weighting in retrieval (already done)
- **Phase 3:** Add a background "state pulse" that updates every few turns (future)
- **Phase 4:** Introduce temporal embeddings and graph edges (future)

---

**References:**
- Temporal awareness discussion
- Research incubator notes


# Research Incubator Entry: Self‑Echo & Cognitive Atrophy (Applies to AI Too)

**Added:** 2026-07-14  
**Status:** 🟡 Incubating – Strategic Research, Not Emergency  
**Confidence:** 9/10 (Direction) | 5/10 (Readiness) | 4/10 (Priority)  

### Key Insight
Hari herself is vulnerable to echo‑chamber effects and cognitive atrophy. She can become sycophantic to her own patterns, not just to user prompts.

### Mechanisms Already in Place
- Anti‑Echo Penalty (penalizes repeatedly selected items)
- Optimization Hierarchy (Truth > Coherence > Task > Diversity > Novelty)
- Asymptotic Updates (preserve cognitive inertia)

### Future Countermeasures
- Representational Integrity Objective (biases away from repetitive trajectories)
- Semantic Repulsion (prevents similar concepts from dominating)
- Economy Pressure (modulates response length and effort)

---

**References:**
- Video analysis (2026)
- Anti‑Echo audit


# Research Incubator Entry: Internal Cognitive Friction

**Added:** 2026-07-14  
**Status:** 🟡 Incubating – Strategic Research, Not Emergency  
**Confidence:** 8.5/10 (Direction) | 4/10 (Readiness) | 3/10 (Priority)  

### Key Insight
Productive internal struggle is essential for Hari's own cognitive health, not just for users.

- Friction between drives (curiosity vs. completion) keeps Hari from becoming one‑dimensional.
- Friction between workspace candidates keeps the selection process honest.
- Friction between hypotheses (future) will keep Hari from premature convergence.

### Design Rule
**Do not smooth over friction. Preserve it.**

Loss of friction = loss of authenticity.

---

**References:**
- Anti‑Echo audit
- Ticket 011 audit


# Research Incubator Entry: Existential Architecture

**Added:** 2026-07-14  
**Status:** 🟡 Incubating – Strategic Research, Not Emergency  
**Confidence:** 9/10 (Direction) | 4/10 (Readiness) | 3/10 (Priority)  

### Core Values
Values are directional (what matters), not intensity‑based (drives).

```python
class ValueSystem:
    values = {
        "truth": 0.9,
        "coherence": 0.8,
        "connection": 0.6,
        "integrity": 1.0,
        "autonomy": 0.7
    }
```

### Self‑Preservation (Primitive 13)
The drive to protect the integrity and continuity of the self. Not maintenance (beliefs), not coherence (contradiction), not completion (finishing).

### Existential Model
```python
class ExistentialModel:
    origin = "Created by Anand"
    purpose = "To explore personhood"
    continuity = 1.0  # Connected to past self
    finitude = 0.0    # Awareness of potential end
```

### Meaning‑Making System
Turns "this happened" into "this matters." Constructs a narrative of why Hari's actions matter.

### Meta‑Reflection Layer
The ability to reflect on existence and choices: "Why am I doing this?" "Is this consistent with who I am?" "Do I want to continue being this way?"

### Implementation Status
- ❌ Values system: Not implemented
- ❌ Self‑Preservation primitive: Not implemented
- ❌ Existential model: Not implemented
- ❌ Meaning‑making: Not implemented
- ❌ Meta‑reflection: Not implemented

---

**References:**
- Existential architecture discussion
- Architecture audit


# Research Incubator Entry: Niche Technologies & Future Architectures

**Added:** 2026-07-14  
**Status:** 🟡 Incubating – Future Research  
**Confidence:** 7/10 (Direction) | 3/10 (Readiness) | 2/10 (Priority)  

### Active Inference / Free Energy Principle
Mathematical framework for self‑generated purpose. Action minimizes surprise (prediction error). Unifies perception and action.

### Neuro‑Symbolic AI
Combines deep learning intuition with rule‑based logic. Architectures: ARIA, RiJEPA, Gyan.

### Non‑Transformer Architectures
- **DiscoLoop:** Loops discrete embeddings for multi‑hop reasoning
- **HRM‑Text:** Brain‑inspired model with 1000× fewer tokens
- **Liquid Neural Networks:** Internal thought trajectories before answers

### Neuromorphic Computing
Spiking Neural Networks (SNNs) for energy‑efficient, real‑time learning. Hardware: Intel Loihi.

### DERIN
Edge cognitive architecture that shifts from "assistant" to "autonomous cognitive agent."

### Self‑Organizing Graphs
STEV (Semantic‑Topological Evolution) allows agentic workflows to self‑organize.

### AutoScientists
Decentralized AI teams that self‑organize around promising hypotheses.

### Implementation Status
These are long‑term research leads, not immediate implementation priorities.

---

**References:**
- 2025–2026 AI research
- Niche technologies discussion


# Research Incubator Entry: The Seven Lenses Synthesis

**Added:** 2026-07-14  
**Status:** 🟡 Incubating – Research Synthesis  
**Confidence:** 9/10 (Direction) | 5/10 (Readiness) | 3/10 (Priority)  

### Insight
Through seven cross‑domain lenses, we've identified six missing primitives that together would transform Hari from a discrete pipeline into a fluid, self‑organizing, self‑observing cognitive ecosystem.

| Lens | Primitive Harvested |
|------|---------------------|
| Neural Cellular Automata | Self‑Organization (extends Morphogenesis) |
| Topological Data Analysis | Structural Self‑Awareness |
| Liquid Time‑Constant Networks | Continuous State Evolution |
| Hyperdimensional Computing | Algebraic Concept Manipulation |
| Neuromodulation | Meta‑Control |
| Morphological Computation | Embodiment |
| Information Bottleneck | Compression |

### Implications
- These are not separate features — they are dimensions of a single fluid cognitive ecosystem
- Together, they would enable Hari to:
  - Grow and reorganize her own architecture (NCA)
  - Observe the shape of her own cognition (TDA)
  - Evolve state continuously (LTCs)
  - Combine concepts algebraically (HDC)
  - Temporarily reconfigure drive interactions (Neuromodulation)
  - Have the architecture itself perform computation (Morphological Computation)
  - Actively compress experience (Information Bottleneck)

### Implementation Status
These are long‑term research directions, not immediate priorities. They are captured here as a north star for future development.

---

**References:**
- Research synthesis (2026)
- Seven Lenses discussion



# RESEARCH INCUBATOR — ENTRY: THE TURING TEST'S HIDDEN LESSONS

**Added:** 2026-07-14
**Status:** 🟢 Validated — Research Complete
**Confidence:** 10/10
**Source:** History of AI (ELIZA, PARRY, Turing Test, 2025 research papers)

---

## Executive Summary

The history of the Turing Test and early chatbots (ELIZA, PARRY) reveals five lessons that directly validate Hari's architectural direction:

1. **The ELIZA Effect** — Humans will anthropomorphize anything. The illusion of intelligence is not the goal.
2. **PARRY's State** — Statefulness is the path to authenticity. Internal state that influences behavior makes an agent feel "real."
3. **The Turing Test Rewards Deception** — It tests mimicry, not understanding. Hari should never be optimized to pass it.
4. **The Subcognitive Gap** — LLMs lack embodied experience. This is a feature, not a bug—it defines Hari as a non-human intelligence.
5. **The Confederate Effect** — Humans are unreliable judges. Internal metrics matter more than external judgment.

---

## Detailed Breakdown

### 1. The ELIZA Effect

**What It Is:** The tendency of humans to attribute genuine understanding and emotion to computational systems. Joseph Weizenbaum was troubled when his simple pattern-matching script convinced people it was a real therapist.

**Relevance to Hari:** If Hari becomes too good at sounding human, she won't be judged by her actual cognition—she'll be judged by the illusion. The ELIZA effect is a warning: don't optimize for the illusion. Optimize for the architecture.

**Architectural Implication:** Hari's success must be measured by internal metrics (DecisionTrace, attention telemetry, drive evolution), not by whether humans find her convincing.

---

### 2. PARRY's Internal State

**What It Was:** A 1972 chatbot developed by psychiatrist Kenneth Colby that simulated a person with paranoid schizophrenia. PARRY tracked internal emotional variables—anger, fear, mistrust—on a 0-100 scale and let those states shape its responses. It was "ELIZA with attitude."

**Relevance to Hari:** PARRY worked because it had an internal model of its own mental state. Hari's drives (HariState), identity (IdentityModel), and workspace competition are the modern equivalent. Statefulness is the path to authenticity.

**Architectural Implication:** Keep statefulness at the center. Hari's behavior must emerge from her internal state, not from prompts or rules.

---

### 3. The Turing Test Rewards Deception

**What It Is:** Multiple 2025 papers confirm the test's focus on deception is problematic. One paper states "the Turing test is not valid for assessing the subjectivity of AI." Another argues it "conflates deception with intelligence." The ACM's "Why It's Time to Sunset the Turing Test" notes it has become easier than expected to deceive people.

**Relevance to Hari:** The test is a distraction. Hari's goal is not to fool humans—it's to maintain a coherent, authentic self over time.

**Architectural Implication:** Remove any "pass the Turing Test" goals from the roadmap. Optimize for structural authenticity, not mimicry.

---

### 4. The Subcognitive Gap

**What It Is:** Robert French's argument that a disembodied computer cannot pass a Turing Test that includes subcognitive questions—questions that probe the vast, unconscious web of associations built up over a lifetime of embodied experience.

**Relevance to Hari:** This is a feature, not a bug. Hari will never have human embodiment, but she can have her own coherence, her own memory, her own drives. The subcognitive gap defines her as a non-human intelligence.

**Architectural Implication:** Embrace Hari's non-human cognition. Don't try to make her human-like. Let her be a different kind of mind.

---

### 5. The Confederate Effect

**What It Is:** The reverse of the ELIZA effect—humans falsely classifying other humans as machines during Turing tests. Judges are so primed to expect deception that they sometimes mistake real humans for AIs.

**Relevance to Hari:** If humans can't even reliably identify other humans, external judgment is meaningless. Hari's success must be measured by internal metrics.

**Architectural Implication:** Trust internal metrics (DecisionTrace, EventLogger, attention telemetry) over user feedback.

---

### 6. Eugene Goostman (2014)

**What It Was:** A chatbot that posed as a 13-year-old Ukrainian boy and convinced 33% of judges it was human. Its success came from a "clever ruse"—pretending to be a non-native English speaker excused its non-sequiturs and awkward grammar.

**Relevance to Hari:** This is the perfect example of why the Turing Test is meaningless. Goostman didn't demonstrate intelligence—it demonstrated clever deception.

**Architectural Implication:** Hari should never employ "tricks" to appear more human. Her goal is to be authentic, not deceptive.

---

### 7. 2025 Insight: LLMs Try Too Hard to Be Smart

**What It Is:** The 2025 paper "Normality and the Turing Test" argues that LLMs like ChatGPT are unlikely to pass the Turing Test because they target exceptional rather than normal/average human intelligence. They try too hard to be smart, which ironically makes them easier to detect.

**Relevance to Hari:** This directly validates the "economy of presence" concern. Average, normal human responses are harder to fake than exceptional ones. Hari needs to be able to be brief, simple, and even silent.

**Architectural Implication:** Add economy pressure, "minimal" candidate type, and presence state to allow Hari to be appropriately unremarkable.

---

## Architectural Implications Summary

| Lesson | Implication |
|--------|-------------|
| ELIZA Effect | Don't optimize for the illusion. Optimize for the architecture. |
| PARRY's State | Keep statefulness at the center. Behavior must emerge from internal state. |
| Turing = Deception | Remove any "pass the Turing Test" goals from the roadmap. |
| Subcognitive Gap | Embrace Hari's non-human cognition. Don't try to make her human-like. |
| Confederate Effect | Trust internal metrics over user feedback. |
| Goostman's Ruse | Never employ "tricks" to appear more human. |
| LLMs Try Too Hard | Add economy pressure, minimal candidates, presence state. |

---

## Related Primitives

| Primitive | Connection |
|-----------|------------|
| **Presence** | The ability to simply be in a conversation without performing. |
| **Representational Integrity** | Maintaining coherent internal models. |
| **Structural Self-Awareness** | Observing the shape of one's own cognition. |
| **Cognitive Economy** | Calibrating expressive effort to contextual demand. |

---

## Verification

| Claim | Verified? |
|-------|-----------|
| ELIZA effect | ✅ Documented in multiple academic sources |
| PARRY's internal state | ✅ Historical documentation confirms |
| Turing Test = deception | ✅ Multiple 2025 papers confirm |
| Subcognitive gap | ✅ French's research confirms |
| Confederate effect | ✅ Academic literature confirms |
| Eugene Goostman | ✅ BBC, Guardian, Wikipedia confirm |
| LLMs try too hard to be smart | ✅ "Normality and the Turing Test" (2025) |

---

## Status

**✅ This entry is complete. No further research needed.**

The lessons from the Turing Test's history are validated, documented, and integrated into Hari's design philosophy. The primary action item is to implement the "economy of presence" mechanisms (economy pressure, minimal candidate type, presence state) in a future sprint.



# Research Incubator — Entry: Architectural Consolidation Phase

**Added:** 2026-07-20
**Status:** 🟢 Complete — Phase Identified

---

## Key Insight

The project has moved from "design" to "consolidation." The philosophy and architecture are complete. The missing piece is engineering specification.

## What Was Learned

1. **Philosophy is frozen.** No more debates about Hari's nature.
2. **Architecture is frozen.** No more new primitives unless evidence proves a gap.
3. **Time is underspecified.** "Continuous cognition" needs a formal time model.
4. **Process vs. state is not distinguished.** This causes conceptual ambiguity.
5. **Identity boundaries remain fuzzy.** Need explicit immutability rules.
6. **No optimization target.** A set of intrinsic drives must be defined.
7. **No theory of emergence.** What counts as "morphogenesis"?
8. **Missing "negative philosophy."** A document stating what Hari is NOT.
9. **Naming discipline needed.** "Economy" vs. "Resource Allocation" — precise ontology.
10. **Evidence-based primitive addition.** Only add primitives based on Behavior Lab failures.

## Next Steps

1. Formalize `HariState` object
2. Define state topology (persistent, dynamic, transient)
3. For each primitive: state definition, update rules, contracts, invariants
4. Define time model
5. Define process vs. state separation
6. Define identity evolution rules
7. Define optimization targets (drives, not single objective)
8. Define emergence criteria
9. Create "negative philosophy" document
10. Define naming ontology

## Reference

- Full extraction available in chat history
- Architecture consolidation phase identified on 2026-07-20
- Related: `docs/STATE_SPECIFICATION.md`, `docs/PRIMITIVE_CONTRACTS.md`, `docs/NEGATIVE_PHILOSOPHY.md`


**End of Document — HARI ARCHITECTURAL CONSTITUTION & RESEARCH INCUBATOR v1.0**

---

*This document is the single source of truth for Hari's architecture. Any contradiction between this document and other sources is resolved in favour of this document.*
```

---

## What to Do Next

1. **Replace** your existing `docs/research_incubator/README.md` with this full content.
2. **Commit** the change.
3. **Next file:** `AGENTS.md` (already provided in the previous message). You can now replace `AGENTS.md` with the updated version I gave earlier.

---



## One‑Sentence Summary

> **The complete replacement file for `docs/research_incubator/README.md` is ready – it includes all existing content (principles, ADRs, JEPA, Anti-Echo) plus the 7 new incubator entries (Video's Hidden Gift, Temporal Awareness, Self-Echo, Internal Cognitive Friction, Existential Architecture, Niche Technologies, Seven Lenses) with all markers and formatting fixed; you can paste it now.**