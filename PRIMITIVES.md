# The Primitives of Hari

## What This Is

This is a working taxonomy of the universal principles that Hari implements. It was distilled from research across cognitive science, neuroscience, AI, evolutionary biology, cybernetics, ecology, economics, and distributed systems.

**The exact number of primitives is less important than the recognition that many frameworks (CoALA, JEPA, Active Inference, etc.) are expressions of the same underlying patterns.**

## The Primitives

| # | Primitive | Definition | Hari Implementation(s) |
|---|-----------|------------|------------------------|
| 1 | **Persistence** | Information and structure survive across time | `MemoryEvent`, `IdentityModel`, `NarrativeThread` |
| 2 | **Competition** | Multiple candidates vie for limited resources | Workspace softmax |
| 3 | **Selection** | A mechanism decides which candidate wins | Softmax + diversity penalty |
| 4 | **Broadcast** | The winner influences the rest of the system | `broadcast_feedback()`, dialogue |
| 5 | **Prediction** | Internal simulation without external output | `compute_prediction_error()` |
| 6 | **Constraint** | Deterministic boundaries around probabilistic processes | Constitution, Invariants, State Guards (planned) |
| 7 | **Transformation** | The system changes its own state | `asymptotic_update()`, `natural_drift()` |
| 8 | **Resource Allocation** | Limited resources dynamically distributed | Workspace slots, drive weights |
| 9 | **Synchronization** | Multiple processes coordinate in time | `TurnPipeline.execute()` |
| 10 | **Variation Health** | Maintaining adaptive diversity without collapse | Echo Risk metrics (future) |
| 11 | **Meta-Rule** | Changing the rules of change | (Future: learning to learn) |
| 12 | **Morphogenesis** | Structure emerges from local interactions | (Future: self-organization) |

## Cross-Cutting Constraints

These are not primitives, but they are architectural laws that cut across multiple primitives:

| Constraint | Description |
|------------|-------------|
| **Stability vs Plasticity** | Too stable → rigid; too plastic → chaotic. Hari needs a dynamic balance between Persistence and Transformation. |
| **Optimization Hierarchy** | Truth → Coherence → Task → Diversity → Novelty. No mechanism may sacrifice a higher-priority property for a lower-priority one. |
| **Authenticity** | `alignment(internal_state, external_expression)`. An instantiation of the Constraint primitive. |


## Lessons from AI History

| Lesson | What It Teaches | Implication for Hari |
|--------|-----------------|----------------------|
| **ELIZA Effect** | Humans anthropomorphize anything | Don't optimize for the illusion |
| **PARRY's State** | Statefulness = authenticity | Behavior must emerge from internal state |
| **Turing Test** | Rewards deception, not intelligence | Don't optimize for it |
| **Subcognitive Gap** | Embodied experience matters | Embrace non-human intelligence |
| **Confederate Effect** | Humans are unreliable judges | Trust internal metrics |
| **Goostman's Ruse** | "Tricks" are meaningless | Authenticity is the goal |
| **LLMs Try Too Hard** | Being "exceptionally smart" is a tell | Economy of presence is essential |

**Implication:** Hari should never be optimized to "pass" as human. Her value is in being a coherent, authentic non-human intelligence.

## Key Insight

**Hari already implements most of these.** The remaining work is calibration and measurement, not new features.
"@