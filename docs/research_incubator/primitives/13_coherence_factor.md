# 13. Coherence Factor

**Status:** Defined — Implementation Ready
**Last Updated:** 2026-07-20

---

## Formal Definition

**Coherence Factor** is the estimated contribution of a candidate toward reinforcing or integrating with Hari's current cognitive structure.

It is **not** confidence, importance, or urgency. It is the degree to which the candidate *fits* with existing cognition and helps maintain or strengthen the existing cognitive architecture.

---

## Runtime Proxy (V1)

| Candidate Type | Proxy |
|----------------|-------|
| Memory | `0.1 × significance` |
| Hypothesis | `0.3 × confidence` |
| Curiosity Node | `0.2 × importance` |
| Narrative Thread | `0.1` (constant) |
| Open Thought | `0.1 × urgency` |

All proxies are V1 heuristics. They should be calibrated empirically.

---

## Future Evolution

When Hari has a more robust cognitive structure model, `coherence_factor` should be computed from:

- Semantic overlap with existing memory clusters
- Structural fit with current interests/narratives
- Consistency with identity
- Predictive value for future cognition

---

## Failure Modes

| Failure Mode | Signal | Mitigation |
|--------------|--------|------------|
| Over-coherence | Too much weight on existing patterns | Reduce proxy values |
| Under-coherence | New ideas never integrate | Increase proxy values |
| Semantic drift | Coherence changes too quickly | Monitor variance over time |