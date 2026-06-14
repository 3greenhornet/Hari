# Hari Cognitive Ecology – Transformation Laws

This document defines how cognitive objects evolve. No subsystem may bypass these rules.

## Objects

- `MemoryEvent` – raw turn
- `Pattern` – recurring thematic cluster (future)
- `Contradiction` – unresolved conflict between beliefs/models
- `CuriosityNode` – specific question
- `Interest` – long‑term intellectual gravity
- `NarrativeThread` – ongoing story arc
- `Hypothesis` – structured belief about user/self/world
- `IdentityModel` – evolving self‑understanding
- `RelationshipModel` – per‑user relational state

## Transformation Rules

1. **Memory → Pattern**  
   When ≥3 episodic memories share high thematic similarity (embedding cosine >0.8), create a `Pattern`.

2. **Pattern → Contradiction**  
   When a `Pattern` conflicts with an existing `Hypothesis` (or `IdentityModel` principle), create a `Contradiction` with severity proportional to the confidence of both sides.

3. **Contradiction → Curiosity**  
   Every active `Contradiction` generates a `CuriosityNode` ("Why does X conflict with Y?"). This node competes in the workspace.

4. **Curiosity → Interest**  
   If the same thematic topic generates ≥5 `CuriosityNode`s across ≥3 distinct sessions (or simulated turns), consolidate into an `Interest`.

5. **Interest → Investigation**  
   When an `Interest` has high urgency (time since last activation), inject a proactive `WorkspaceCandidate` to explore it.

6. **Investigation → Narrative**  
   Sustained (≥10 turns) active pursuit of a topic becomes a `NarrativeThread`.

7. **Narrative → Identity**  
   When a `NarrativeThread` reaches `completion_estimate > 0.8`, extract a core lesson and update `IdentityModel.self_narrative`.

8. **Relationship → Identity**  
   `RelationshipModel.trust_index` and `shared_discoveries` bias `IdentityModel.core_commitments` slowly (Δ < 0.01 per turn).

## Prohibitions

- No object may be deleted without passing through `archive_inactive_structures()`.
- No subsystem may create a `NarrativeThread` or `Interest` directly – only via `PromotionEngine`.
- No heuristic rules that bypass these transformation laws.