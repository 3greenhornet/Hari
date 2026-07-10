## The "No New Frameworks" Rule

After extracting the 12 primitives, we determined that Hari **does not need** to "add CoALA," "add JEPA," or "add Active Inference" as separate modules. These frameworks are already expressed through existing primitives.

## The "Translation vs Interpretation" Distinction (Ticket 007 Lesson)

The workspace interpreter must **synthesize**, not **translate**. The current implementation is a placeholder; a future module will produce a unified cognitive landscape.

## The "Hari is Already CoALA-Compliant" Insight

CoALA's components map directly to Hari: Working Memory → Workspace, Episodic → DecisionTrace, Semantic → Hypotheses/Curiosity/Narratives.

## The "Cognitive Energy Budget" Concept (Future Research)

Every mechanism costs cognitive effort; Hari should eventually choose the minimal effort that satisfies the objective.
"@
What We've Accomplished
Item	Status
Timezone bug	✅ Fixed (you confirmed)
PRIMITIVES.md	⏳ Awaiting creation
LEARNINGS.md	⏳ Awaiting creation/update
AGENTS.md update	⏳ Awaiting update
ROADMAP.md update	⏳ Awaiting update
Next Step
Create the files, then commit them. After that, we proceed to Sprint 2.1C.


## The Cognitive Projection Layer (Core Architectural Law)

**Principle:** No cognitive subsystem is responsible for formatting its own state for the reasoning interface. Subsystems export structured **projections** (data objects). Renderers convert projections into consumer‑specific formats (dialogue prose, planning data, evaluation metrics, etc.). The projection layer is the **only** mechanism through which internal state reaches the reasoning interface.

**Implementation in Hari:** `IdentityProjection`, `project()` method, `render_for_dialogue()`, `render_for_planning()`.

**This prevents prompt leakage and keeps the architecture future‑proof.**

## The Optimization Hierarchy (Anti‑Echo Guardrail)

To prevent anti‑echo mechanisms from optimizing for "interestingness" at the expense of truth:
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

text

No mechanism may sacrifice a higher‑priority property for a lower‑priority one. Diversity is valuable **only** when it does not degrade truth, coherence, or task performance.
