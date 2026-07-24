# 14. Trajectory Deviation

**Status:** Defined — V1 Implementation
**Last Updated:** 2026-07-20

---

## Formal Definition

**Trajectory Deviation** is the continuous estimate of how much the current conversation has departed from the active cognitive thread.

It is **not** avoidance detection. It is an **observable signal** about conversation trajectory. "Avoidance" is a higher-level interpretation that Hari may infer from this signal.

---

## Runtime Signals

| Field | Type | Description |
|-------|------|-------------|
| `trajectory_deviation` | float (0.0–1.0) | 0.0 = continuing thread, 1.0 = complete departure |
| `trajectory_confidence` | float (0.0–1.0) | Confidence in the estimate |
| `referenced_thread_id` | optional string | ID of the thread being deviated from |

---

## Context Grounding

The active narrative thread (title, description, open questions) is passed into the monologue prompt so the LLM can evaluate trajectory relative to actual runtime objects.

---

## State Integration

Trajectory deviation updates (continuous, scaled by confidence):

| State Field | Update | Source |
|-------------|--------|--------|
| `social_ambiguity` | `+= deviation × confidence × 0.3` | MONOLOGUE |
| `completion` | `+= deviation × confidence × 0.2` | MONOLOGUE |
| `cognitive_tension` | `+= deviation × confidence × 0.1` | MONOLOGUE |

---

## Workspace Integration

When `trajectory_deviation > 0.2` and `trajectory_confidence > 0.3`, an `open_thought` candidate is injected with urgency = `deviation × confidence`.

This is a workspace admission policy, not part of the primitive definition.

---

## V1 Implementation

| Component | Implementation |
|-----------|----------------|
| **Estimator** | LLM-based (monologue) |
| **Context** | Active thread (title, description, open questions) |
| **Output** | `trajectory_deviation`, `trajectory_confidence`, `referenced_thread_id` |

---

## Future Evolution (V2+)

Replace LLM-only estimation with fusion of multiple runtime signals:

1. LLM estimate
2. Thread continuity metrics
3. Prediction error
4. Conversation graph distance
5. Unresolved question persistence

---

## Failure Modes

| Failure Mode | Signal | Mitigation |
|--------------|--------|------------|
| False positive | High deviation when no deviation | Track confidence; require >0.3 |
| False negative | Low deviation when actual deviation | Monitor referenced_thread_id grounding |
| Low confidence | Uncertainty drives behavior | State updates scale by confidence |
| Hallucination | referenced_thread_id doesn't exist | Cross-check against active thread IDs |

---

## Verification Criteria

Ticket 014 is successful when:
1. `trajectory_deviation` and `trajectory_confidence` are logged
2. State updates occur continuously (scaled by confidence)
3. `referenced_thread_id` is either null or an actual active thread ID
4. Workspace candidate appears when deviation > 0.2 and confidence > 0.3
5. No hardcoded thresholds in the primitive definition
6. Future migration path documented