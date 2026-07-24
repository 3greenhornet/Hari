# Primitive Contracts

**Version:** 1.0
**Last Updated:** 2026-07-20
**Status:** Draft — To Be Finalized

---

## Contract Structure

Every primitive must define:

1. **Inputs** — What data does it consume?
2. **Outputs** — What data does it produce?
3. **State Owned** — What state does it own?
4. **State Read** — What state does it read?
5. **Invariants** — What must always be true?
6. **Failure Modes** — What can go wrong?
7. **Update Rule** — How does it update?

---

## 1. Workspace

| Field | Value |
|-------|-------|
| **Inputs** | Memories, hypotheses, curiosity nodes, narrative threads, open thoughts |
| **Outputs** | Selected workspace items, attention weights |
| **State Owned** | Current workspace items, activation metrics |
| **State Read** | Drives (curiosity, completion, coherence), affect (dominance) |
| **Invariants** | Workspace size ≤ 7; All items have scores [0,1] |
| **Failure Modes** | No candidates → fallback; All candidates low → stochastic selection |
| **Update Rule** | Softmax competition with pressure fields |

---

## 2. Economy

| Field | Value |
|-------|-------|
| **Inputs** | Rest drive, engagement drive |
| **Outputs** | Economy pressure [0,1] |
| **State Owned** | Economy pressure |
| **State Read** | Rest, engagement |
| **Invariants** | Economy pressure ∈ [0,1] |
| **Failure Modes** | Too high → suppresses expression; Too low → no brevity pressure |
| **Update Rule** | `rest_excess = max(0, rest - 0.4); disengagement_excess = max(0, (1 - engagement) - 0.5); economy = min(1, (rest_excess + disengagement_excess) / 1.1)` |

---

## 3. Curiosity

| Field | Value |
|-------|-------|
| **Inputs** | Contradictions, open questions, prediction errors |
| **Outputs** | Curiosity drive [0,1] |
| **State Owned** | Curiosity drive |
| **State Read** | Workspace, memory, trajectory |
| **Invariants** | Curiosity ∈ [0,1] |
| **Failure Modes** | Too high → exploration overwhelms; Too low → no engagement |
| **Update Rule** | Asymptotic update based on contradiction density + prediction error |

---

## 4. Memory

| Field | Value |
|-------|-------|
| **Inputs** | Conversation events |
| **Outputs** | Retrieved memories, significance updates |
| **State Owned** | Long-term memory, significance scores |
| **State Read** | Workspace, trajectory |
| **Invariants** | Significance ∈ [0,1]; Memory count < 1000 |
| **Failure Modes** | No retrieval → fallback; Significance collapse → all memories equal |
| **Update Rule** | Additive storage; Significance = retrieval reinforcement + decay |

---

## 5. Trajectory

| Field | Value |
|-------|-------|
| **Inputs** | Current thread, open questions, user input |
| **Outputs** | Trajectory deviation [0,1], confidence [0,1] |
| **State Owned** | Trajectory deviation, confidence |
| **State Read** | Narrative threads, prediction error |
| **Invariants** | Deviation ∈ [0,1]; Confidence ∈ [0,1] |
| **Failure Modes** | False positives → over-detection; False negatives → missing shifts |
| **Update Rule** | Monologue estimate + prediction error + thread continuity |

---

## 6. Relationship

| Field | Value |
|-------|-------|
| **Inputs** | Interaction events, social interpretation |
| **Outputs** | Trust, familiarity, reciprocity updates |
| **State Owned** | Trust, familiarity, reciprocity scores |
| **State Read** | Engagement, sincerity estimate |
| **Invariants** | All scores ∈ [0,1] |
| **Failure Modes** | Trust stuck at 0; Familiarity maxed out forever |
| **Update Rule** | Glacial updates: `value = value + delta`; Decay: `value = value * 0.999 + baseline * 0.001` |

---

## 7. Forgetting

| Field | Value |
|-------|-------|
| **Inputs** | Current turn, memory significance |
| **Outputs** | Decayed significance |
| **State Owned** | Memory significance |
| **State Read** | Last retrieved turn, usage count |
| **Invariants** | Decay factor ∈ [0.95, 0.999]; Protection window ≥ 3 |
| **Failure Modes** | Over-forgetting → memory loss; Under-forgetting → memory pollution |
| **Update Rule** | `significance = significance * 0.99; if last_retrieved_turn > current_turn - 3: protect` |

---

## 8. Social Interpretation

| Field | Value |
|-------|-------|
| **Inputs** | Thematic continuity, trajectory deviation, engagement, history |
| **Outputs** | Shift magnitude, sincerity estimate |
| **State Owned** | Shift magnitude, sincerity estimate |
| **State Read** | Monologue output, interaction state |
| **Invariants** | Shift magnitude ∈ [0,1]; Sincerity ∈ [0,1] |
| **Failure Modes** | Over-sensitive → false positives; Under-sensitive → misses shifts |
| **Update Rule** | `shift = 0.4*(1-continuity) + 0.3*trajectory + 0.2*(1-engagement) + 0.1*history` |

---

## 9. Presence

| Field | Value |
|-------|-------|
| **Inputs** | Economy pressure |
| **Outputs** | Presence state [0,1] |
| **State Owned** | Presence |
| **State Read** | Economy pressure |
| **Invariants** | Presence ∈ [0,1] |
| **Failure Modes** | Too high → no expression; Too low → always expressive |
| **Update Rule** | `presence = economy * 0.5` |

---

## 10. Identity

| Field | Value |
|-------|-------|
| **Inputs** | Development events, perspective shifts |
| **Outputs** | Identity projection |
| **State Owned** | Constitution, origin, self-narrative, core commitments |
| **State Read** | Memory, relationships |
| **Invariants** | Constitution immutable; Origin immutable; Self-narrative evolves slowly |
| **Failure Modes** | Identity drift; Contradictory self-narratives |
| **Update Rule** | Only updates via DevelopmentEvent |