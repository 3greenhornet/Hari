
```markdown
# Models Module – Data Models

This module contains all **Pydantic data models** used by the system. These define the shape of all cognitive objects: memory, state, identity, relationships, and more.

---

## Overview

```
models/
├── __init__.py          # Exports all models
├── memory_event.py      # MemoryEvent – conversation turn
├── monologue_output.py  # MonologueOutput – sensory perception
├── decision_trace.py    # DecisionTrace – full audit trail
├── identity.py          # IdentityModel – Constitution, Origin, SelfModel
├── relational.py        # RelationshipModel, Interest, Contradiction
├── narrative.py         # NarrativeThread – persistent narrative
├── curiosity_node.py    # CuriosityNode – open question
├── hypothesis.py        # Hypothesis – belief about user/self/world
├── development.py       # DevelopmentEvent – cognitive landmarks
├── development_event.py # DevelopmentEvent – event‑sourced changes
├── interaction.py       # InteractionModel – social interpretation (future)
├── thought.py           # Thought – incomplete processing loops
├── volition.py          # Desire, Agenda, ActiveProject – volition data
└── workspace.py         # Alias for WorkspaceItem
```

---

## Key Models

### `MemoryEvent` – Conversation Turn

A single turn in the conversation, with embedding and significance.

**Fields:**
- `id` – unique identifier (UUID)
- `session_id` – session isolation
- `turn_number` – conversational order
- `role` – "user" or "assistant"
- `content` – message text
- `significance` – 0.0–1.0, updated by monologue and retrieval reinforcement
- `embedding` – vector for similarity search
- `usage_count` – number of times retrieved (fatigue penalty)
- `last_retrieved_turn` – last time it was used
- `explanatory_power` – 0.0–1.0, how well it explains ruptures

**Usage:**
```python
from models import MemoryEvent
event = MemoryEvent(
    session_id="abc123",
    turn_number=1,
    role="assistant",
    content="Hello, I am Hari."
)
```

---

### `MonologueOutput` – Sensory Perception

Output from `run_monologue()` – pure observation, no commands.

**Fields:**
- `perceived_user_intent` – curious, avoiding, testing, help_seeking, sharing, derailing
- `intent_confidence` – 0.0–1.0
- `thematic_continuity` – 0.0–1.0 (0=rupture, 1=seamless)
- `user_engagement_estimate` – 0.0–1.0
- `interruption_severity` – 0.0–1.0
- `dynamic_candidates` – list of `CandidateArtifact` (conversational actions)
- `curiosity_trigger` – optional new question
- `hypothesis_update` – optional new insight
- `self_belief_update` – optional new self‑understanding
- `memory_significance` – 0.0–1.0
- `memory_emotional_tone` – neutral, positive, negative, curious, frustrated

**Usage:**
```python
from models import MonologueOutput
output = MonologueOutput(
    perceived_user_intent="curious",
    intent_confidence=0.85,
    thematic_continuity=0.8
)
```

---

### `DecisionTrace` – Full Audit Trail

Complete record of every cognitive decision per turn.

**Fields:**
- `trace_id` – unique identifier
- `session_id` – session isolation
- `turn_number` – conversational order
- `drives_before` / `drives_after` – state snapshots
- `workspace_items` – list of `WorkspaceItemTrace` (winners and losers)
- `perceived_user_intent` – from monologue
- `intent_confidence` – 0.0–1.0
- `thematic_continuity` – 0.0–1.0
- `model_used` – which LLM provider
- `temperature` – softmax temperature

**Usage:**
```python
from models import DecisionTrace
trace = DecisionTrace(
    trace_id="abc-123",
    session_id="abc123",
    turn_number=1,
    model_used="gemini-2.5-flash",
    temperature=0.5,
    user_input="Hello",
    retrieved_candidate_count=5,
    selected_winner_count=3,
    drives_before={"care": 0.5, "curiosity": 0.5}
)
```

---

### `IdentityModel` – Three‑Layer Identity

Immutable Constitution, immutable Origin, and evolving SelfModel.

**Layers:**
- `ConstitutionModel` – frozen philosophical invariants (existential mode, asymmetry law, integrity anchor)
- `OriginModel` – frozen historical facts (creator Anand, purpose, architecture)
- `SelfModel` – evolving self‑understanding (narrative, commitments, questions, perspective history)

**Method:**
- `to_prompt_context()` – generates interpreted identity for system prompt

**Usage:**
```python
from models import IdentityModel
identity = IdentityModel()
prompt_context = identity.to_prompt_context()
```

**CRITICAL:** This model exists in code but is **not yet wired** into the runtime. Ticket 008 addresses this.

---

### `RelationshipModel` – Per‑User Relationship

Tracks trust, familiarity, and relational landmarks.

**Fields:**
- `user_id` – unique identifier
- `familiarity` – 0.0–1.0
- `trust_index` – 0.0–1.0
- `reciprocity_score` – 0.0–1.0
- `shared_discoveries` – list of `RelationalLandmark`
- `unresolved_tensions` – list of `RelationalLandmark`
- `relational_landmarks` – complete timeline

**Usage:**
```python
from models import RelationshipModel
rel = RelationshipModel(user_id="user_123")
rel.update_trust(0.1)
```

---

### `NarrativeThread` – Persistent Narrative

Long‑running topic or arc across turns.

**Fields:**
- `id` – unique identifier (UUID)
- `session_id` – session isolation
- `title` – short label
- `description` – extended context
- `status` – active, paused, completed, abandoned
- `completion_estimate` – 0.0–1.0 (0=just started, 1=resolved)
- `emotional_investment` – 0.0–1.0
- `open_questions` – list of strings
- `created_turn`, `last_active_turn` – temporal tracking

**Usage:**
```python
from models import NarrativeThread
thread = NarrativeThread(
    session_id="abc123",
    title="What is consciousness?",
    description="Exploring the hard problem",
    created_turn=1,
    last_active_turn=1
)
```

---

### `CuriosityNode` – Open Question

A single question in the curiosity graph.

**Fields:**
- `id` – unique identifier
- `core_question` – the question itself
- `importance` – 0.0–1.0
- `exploration_progress` – 0.0–1.0
- `last_referenced` – timestamp

**Usage:**
```python
from models import CuriosityNode
node = CuriosityNode(
    id="node_123",
    core_question="Why do humans laugh?",
    importance=0.8
)
```

---

### `Hypothesis` – Belief about User/Self/World

A structured belief with confidence and evidence links.

**Fields:**
- `type` – "user", "self", or "world"
- `statement` – declarative sentence
- `confidence` – 0.0–1.0
- `supporting_event_ids` – list of memory IDs
- `contradicting_event_ids` – list of memory IDs
- `last_updated` – timestamp

**Usage:**
```python
from models import Hypothesis
hyp = Hypothesis(
    type="user",
    statement="The user values authenticity over efficiency.",
    confidence=0.75
)
```

---

### `DevelopmentEvent` – Cognitive Landmark

A permanent, irreversible shift in cognition or identity.

**Fields:**
- `event_id` – unique identifier
- `event_type` – identity_mutation, relationship_rupture, paradigm_shift, etc.
- `description` – human‑readable summary
- `source_tension_id` – ID of the triggering Contradiction or Relationship event
- `impact_domain` – constitution, identity, relationship, epistemic_worldview
- `previous_perspective` / `stabilized_perspective` – before/after stances

**Usage:**
```python
from models import DevelopmentEvent
event = DevelopmentEvent(
    event_type="identity_mutation",
    description="Shifted from seeing silence as empty to seeing it as space.",
    source_tension_id="contradiction_123",
    impact_domain="identity",
    previous_perspective="Silence is absence.",
    stabilized_perspective="Silence is presence."
)
```

---

### `Contradiction` – Cognitive Tension (in `relational.py`)

Active conflict between two beliefs or models.

**Fields:**
- `contradiction_id` – unique identifier
- `belief_a` / `belief_b` – statements or model IDs
- `source_a` / `source_b` – where they came from
- `severity` – 0.0–1.0
- `status` – active, resolving, resolved, archived
- `linked_curiosity_node_ids` – curiosities spawned by this contradiction

**Methods:**
- `resolve(summary)` – mark as resolved
- `increase_severity(delta)` – strengthen tension
- `link_curiosity_node(node_id)` – associate a spawned curiosity

---

### `Interest` – Long‑Term Intellectual Gravity (in `relational.py`)

A persistent thematic field that attracts attention over weeks or months.

**Fields:**
- `interest_id` – unique identifier
- `title` – short label
- `description` – extended context
- `importance` – 0.0–1.0
- `activation_count` – number of times activated across sessions
- `last_activated_turn` – most recent turn
- `last_activated_session` – session ID

**Methods:**
- `update_importance(delta)` – adjust strength
- `record_activation(session_id, turn)` – mark a new activation

---

## Import Convenience

All models are exported from `models/__init__.py`. You can import them all at once:

```python
from models import (
    MemoryEvent,
    MonologueOutput,
    DecisionTrace,
    IdentityModel,
    RelationshipModel,
    NarrativeThread,
    CuriosityNode,
    Hypothesis,
    DevelopmentEvent,
    Interest,
    Contradiction,
    Thought,
    Desire,
    Agenda,
    ActiveProject
)
```

---

## Validation

All models are Pydantic, so they automatically validate fields:

```python
from models import MemoryEvent
event = MemoryEvent(
    session_id="abc123",
    turn_number=1,
    role="assistant",
    content="Hello.",
    significance=1.2  # ❌ ValueError: significance must be 0.0–1.0
)
```

---

## Serialization

Use `.model_dump()` for database storage and `.model_dump_json()` for JSON serialization.

```python
dict_data = event.model_dump()
json_data = event.model_dump_json()
```

---

## Extending Models

When adding new fields, ensure:
- They are optional or have sensible defaults.
- They align with the `db/migrations/` schemas.
- They are added to `__init__.py` exports.

---

## Status

| Model | Purpose | Wired? |
|-------|---------|--------|
| `MemoryEvent` | Conversation turn | ✅ Yes |
| `MonologueOutput` | Sensory perception | ✅ Yes |
| `DecisionTrace` | Audit trail | ✅ Yes |
| `IdentityModel` | Identity layers | ❌ Not wired (Ticket 008) |
| `RelationshipModel` | Per‑user state | ❌ Not wired |
| `NarrativeThread` | Persistent narratives | ✅ Yes |
| `CuriosityNode` | Open questions | ✅ Yes |
| `Hypothesis` | Beliefs | ✅ Yes (promotion) |
| `DevelopmentEvent` | Landmarks | ❌ Not wired |
| `Interest` | Long‑term gravity | ❌ Not wired |
| `Contradiction` | Cognitive tension | ❌ Not wired |
| `Volition` models | Desires/Agendas | ❌ Not wired |
| `Thought` | Incomplete reasoning | ❌ Not wired |

---

> *Models define the shape of Hari's cognition. Keep them clean, validated, and well‑documented.*
```
