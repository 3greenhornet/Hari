# 12. Shared Significance

**Status:** Defined — Implementation Ready
**Last Updated:** 2026-07-20
**Theoretical Influences:** Common Ground Theory, Collaborative Dialogue, Shared Attention

---

## Formal Definition

**Shared Significance** is the estimated importance of a representation because of its role in the evolving shared cognitive context between Hari and another participant, rather than because of its intrinsic informational value.

**It is orthogonal to informational relevance.** A representation may be highly relevant but have little shared significance, or vice versa.

**Shared Significance is computed independently of attention. Attention consumes the estimate but does not define it.**

---

## What It Is NOT

| Concept | Why It's Different |
|---------|-------------------|
| Novelty | Novelty is about newness, not relationship |
| Relevance | Relevance is about the current topic, not the relationship |
| Generativity | Generativity predicts future structure; shared significance evaluates present relationship context |

---

## Runtime Proxy

**Current Runtime Proxy (V1):**
shared_significance = (significance × 0.6) + (care × 0.4)

text

**Proxy Confidence:** LOW. Only uses care and candidate significance. Relationship history unavailable.

---

## Provenance of `significance`

All attention candidates MUST expose `significance` (normalized to [0,1]).

| Candidate Type | Source of Significance |
|----------------|------------------------|
| Memory | Stored significance (updated via retrieval reinforcement) |
| Curiosity Node | Information gain estimate (`importance` field) |
| Narrative Thread | Thread importance (`emotional_investment`) |
| Hypothesis | Explanatory importance (`confidence`) |
| User Input | Social importance (future: from monologue) |

---

## Ownership

- **Owner:** `shared_significance.py`
- **Consumers:** `attention.py`
- **Future Providers:** RelationshipModel

---

## Future Evolution

When RelationshipModel exists, replace the proxy internals with:
relationship_relevance = (care × 0.5) + (trust × 0.3) + (familiarity × 0.2)
shared_significance = (significance × 0.6) + (relationship_relevance × 0.4)

text

The interface to `attention.py` remains unchanged.

---

## Observability

The observatory MUST log:
- Distribution: min, max, mean, std
- Missing significance rate (by candidate type)

---

## Failure Modes

| Failure Mode | Signal | Mitigation |
|--------------|--------|------------|
| Over-attribution | High shared significance for trivial items | Cap at 1.0, monitor distribution |
| Under-attribution | Low shared significance for important items | Ensure care drive updates properly |
| Static significance | Significance never changes | Ensure significance updates with usage |
| Missing significance | Candidate has no `significance` field | Warning in development, log in production |