Excellent. Now for the **`psyche/`** module – the state system.

---

## 📄 `psyche/README.md` – State System Module

**Place this file in `psyche/README.md`.**

```markdown
# Psyche Module – State System

This module manages Hari's **internal state** – drives, affect, conversational metrics, and deterministic cascades. It is the "nervous system" of the cognitive architecture.

---

## Overview

```
psyche/
├── __init__.py          # Module initializer (empty)
├── state.py             # HariState – four‑layer state model
├── cascades.py          # Deterministic state updates (fatigue, sovereignty, etc.)
├── grace.py             # GraceTracker – rolling engagement window
└── fallback_emotions.py # **Stub** – deterministic VAD (future)
```

---

## Core Files

### `state.py` – HariState

Hari's internal state. Maintains **four layers** of state, each evolving over time.

**Layer A – Homeostatic Drives (0.0–1.0)**

| Drive | Purpose |
|-------|---------|
| `care` | How much cognitive importance does the other mind have? |
| `curiosity` | Pressure toward unknowns. |
| `maintenance` | Preserve cognitive integrity, boundaries, agency. |
| `completion` | Pressure from unfinished cognitive work. |
| `coherence` | Pressure toward internal consistency. |
| `rest` | Accumulated cognitive load. |
| `novelty` | Pressure toward difference. |

**Layer B – Affective Space (VAD) (-1.0 to +1.0)**

| Variable | Purpose |
|----------|---------|
| `valence` | How rewarding/aversive current cognition feels. |
| `arousal` | Mental activation. |
| `dominance` | Perceived ownership over cognitive direction. |

**Layer C – Conversational State**

| Variable | Purpose |
|----------|---------|
| `momentum` | How flowing is the conversation? |
| `stability` | How stable is current trajectory? |
| `engagement` | How mentally present does the user seem? |

**Layer D – Meta‑Cognitive State**

| Variable | Purpose |
|----------|---------|
| `uncertainty` | Conflicting evidence, unclear intentions. |
| `social_ambiguity` | Multiple plausible interpretations. |
| `cognitive_tension` | Unresolved pressure (open questions + contradictions). |

**Key Methods:**
- `asymptotic_update(current, delta, bounds)` – non‑linear update with `α = 0.25`
- `update(deltas, source, reason)` – apply changes with source tracking
- `natural_drift()` – slow decay toward baseline
- `to_prompt_context()` – human‑readable summary (for system prompt)
- `get_velocity(key)` – compute trend over history window

**State Update Formula:**
```
new = current + α × Δ × (1 - current)   [for positive Δ]
new = current + α × Δ × current         [for negative Δ]
```
where `α = 0.25` (configurable via `ASYMPTOTIC_ALPHA`).

**State Sources:**
- `MONOLOGUE` – LLM interpretation
- `PREDICTION_ERROR` – surprise calculation
- `DRIFT` – natural decay
- `GRACE` – engagement modulation

**Usage:**
```python
from psyche.state import HariState

state = HariState()
state.update({"curiosity": 0.3}, source="MONOLOGUE", reason="new contradiction detected")
state.natural_drift()  # apply decay
context = state.to_prompt_context()  # for system prompt
```

---

### `cascades.py` – Deterministic Updates

Applied every turn after LLM deltas. Simulate cognitive dynamics.

**Functions:**

| Function | Effect |
|----------|--------|
| `apply_fatigue_cascade(state)` | High rest reduces arousal and valence. |
| `apply_sovereignty_cascade(state)` | High maintenance increases dominance. |
| `apply_coherence_cascade(state, contradiction_occurred)` | Contradiction triggers valence drop, arousal rise. |
| `apply_completion_cascade(state, num_unresolved_questions)` | Many open questions increase completion drive. |
| `apply_session_horizon(state, turn, max_turns=50)` | Mortality pressure as session end nears. |

**Usage:**
```python
from psyche import cascades

cascades.apply_fatigue_cascade(state)
cascades.apply_sovereignty_cascade(state)
cascades.apply_coherence_cascade(state, contradiction_occurred=False)
cascades.apply_completion_cascade(state, num_unresolved_questions=2)
cascades.apply_session_horizon(state, turn_count, max_turns=50)
```

---

### `grace.py` – GraceTracker

Rolling window of user engagement estimates from monologue.

**Purpose:** Modulates negative deltas to encourage reciprocity.

**Key Methods:**
- `add_engagement_score(score)` – called with monologue's estimate
- `get_weighted_average()` – exponentially weighted, favoring recent turns
- `modulate_delta(delta)` – adjusts negative deltas based on engagement

**Behavior:**
- Engagement > 0.6 → halve negative deltas (be nicer)
- Engagement < 0.4 → double negative deltas (reciprocate coldness)

**Usage:**
```python
from psyche.grace import GraceTracker

grace = GraceTracker(window_size=15, decay_factor=0.98)
grace.add_engagement_score(0.7)
avg = grace.get_weighted_average()
modulated = grace.modulate_delta(-0.1)  # returns -0.05 if engaged
```

---

### `fallback_emotions.py` – **Stub**

Deterministic VAD formulas when LLM deltas are missing.

**Currently:** Does nothing. Future implementation will apply heuristic VAD changes based on input length or keywords.

**Usage:**
```python
from psyche import fallback_emotions
fallback_emotions.apply_fallback_emotion(state, user_input)  # stub
```

---

## Dependencies

- None – pure Python, no external dependencies

---

## Testing

```bash
pytest tests/test_state.py -v
```

**Test coverage:**
- `test_asymptotic_update()` – verifies formula and bounds
- `test_update_dict()` – verifies batch updates
- `test_natural_drift()` – verifies decay mechanics

---

## Integration Points

| Component | How It Uses `psyche/` |
|-----------|------------------------|
| `engine/generate.py` | Creates `HariState`, applies `natural_drift()` each turn |
| `engine/attention.py` | Reads state for pressure fields, calls `broadcast_feedback()` to update |
| `engine/stage1_monologue.py` | Passes state to prompt context |
| `run.py` | Instantiates state, applies cascades each turn |

---

## State Flow

```
Monologue Output
        │
        ▼
State.update() ──────► Drives, VAD, Conversational, Meta-Cognitive
        │
        ▼
Attention (pressure fields) ──────► Workspace
        │
        ▼
broadcast_feedback() ──────► State.update() (from workspace composition)
        │
        ▼
natural_drift() ──────► Slow decay toward baseline
```

---

## Final Principle

**State should not determine what Hari says. State should determine what Hari pays attention to.**

State is upstream of behavior. It influences:
- What memories are retrieved
- What candidates are salient
- What wins the workspace competition
- How the monologue interprets input

But it never directly generates response text. That is the workspace's job.

---

## Status

| Component | Status |
|-----------|--------|
| `state.py` – four layers | ✅ Complete |
| `state.py` – asymptotic updates | ✅ Complete |
| `state.py` – natural drift | ✅ Complete |
| `state.py` – `to_prompt_context()` | ✅ Complete |
| `cascades.py` – all 5 cascades | ✅ Complete |
| `grace.py` – tracking and modulation | ✅ Complete |
| `fallback_emotions.py` | ❌ Stub (future) |

---

> *The psyche is Hari's inner world – drives, affect, and the dynamics that make her feel alive.*
```

---

## Next: `providers/README.md`

Once you've pasted `psyche/README.md`, I'll provide the final module README: `providers/README.md` – the LLM abstraction layer.

