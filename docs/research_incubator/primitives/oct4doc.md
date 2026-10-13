# Intention: <name>

Status: seed | partial | ready
Created: <date>
Depends on: <other intentions or code changes that must precede>

## What it is

One paragraph. What would exist if this were built.

## Why it matters

The problem it solves that isn't solved today. Concrete example if possible.

## Where it would live

Specific files and functions. Not "in the engine" — `engine/attention.py::_compute_pressure_field`,
`models/workspace.py`, etc.

## Current state

What exists now, what's missing, why it wasn't done in the last round.

## Rough shape

Formulas, diagrams, structure. Enough that someone could start.

## References

Papers, prior art, or related intentions in this repo.

The seeds themselves
Paste each as its own file. These carry the actual design content from our discussion, not pointers back to it.

docs/intentions/typed_cognitive_candidate.md
text
# Intention: Typed Cognitive Candidate Envelope

Status: seed
Created: 2026-10-04
Depends on: nothing — can be done anytime

## What it is

Every workspace candidate — memories, active thoughts, curiosity nodes,
narratives, hypotheses, volition, contradictions, incoming events —
currently travels as a Python dict. Each producer sets whatever keys it
remembers. Each consumer reads whatever keys it expects. The gap between
the two is where metadata gets lost.

This intention replaces the dict with a single Pydantic class:
CognitiveCandidate.

All producers emit CognitiveCandidate. Attention reads CognitiveCandidate.
Telemetry writes CognitiveCandidate. One type, one schema, one place
where the shape is defined.

## Why it matters

The InternalCandidate field-loss bug (Pydantic stripping intrinsic_relevance
and activation_reason) was the same failure mode: a producer emitted fields
that a downstream consumer needed, and the interface between them silently
dropped them. The memory embedding bug was the same: retrieve_candidates_hybrid
built a MemoryEvent with embedding=None, so attention had no vector to score.

Both bugs were invisible until the trace was checked. A typed envelope
prevents the entire class.

## Where it would live

models/workspace.py — defines CognitiveCandidate
engine/attention.py::load_workspace — accepts List[CognitiveCandidate]
engine/endogenous.py::collect_endogenous_candidates — returns List[CognitiveCandidate]
engine/generate.py::_allocate_workspace — builds List[CognitiveCandidate]
engine/volition_engine.py::get_proactive_candidates — returns List[CognitiveCandidate]

## Current state

Not started. All producers emit dicts with inconsistent keys. The
InternalCandidate and MemoryEvent Pydantic models exist but are not
unified into one candidate type.

## Rough shape

class CognitiveCandidate(BaseModel):
    id: str
    content: str
    item_type: str
    source: str
    origin: str

    urgency: float = 0.0
    persistence: float = 0.0
    intrinsic_relevance: float = 0.0
    internal_activation: float = 0.0

    information_gap: float = 0.0
    closure_pressure: float = 0.0
    coherence_factor: float = 0.0

    activated_by: Optional[str] = None
    activation_reason: Optional[str] = None
    embedding: Optional[List[float]] = None

Then each producer builds one of these. load_workspace iterates them
without needing to know which producer sent which.

This is a refactor, not a fix. Do not do it during a sprint where
you are also changing behavior — the two changes become entangled
and you cannot tell which one caused a regression.

## References

The failure pattern: engine/memory.py → retrieve_candidates_hybrid set
embedding=None after selecting embedding in SQL. models/monologue_output.py
→ InternalCandidate docstring claimed fields the class did not have.
docs/intentions/homeostatic_reward_as_signal.md
text
# Intention: Homeostatic Reward as Selection Signal

Status: seed
Created: 2026-10-04
Depends on: the settle_workspace telemetry fix

## What it is

compute_homeostatic_reward() returns the negative weighted squared distance
from setpoints. It is called once per turn, after the workspace winner is
already selected, and logged. It does not influence selection.

This intention makes reward a selection signal: for each candidate, estimate
what winning it would do to the distance from setpoints, and score the
candidate by whether it moves toward or away from viability.

## Why it matters

The whole point of Hari having drives is that the drives should shape what
she attends to. Right now drives affect salience only through state-modulated
weights on individual pressures. The composite question "would this make my
state better or worse" never enters the competition.

A candidate that resolves cognitive tension should get a boost. A candidate
that would increase uncertainty should be penalized. That is a different
signal from "curiosity is high, so curiosity-flavored candidates get weight."

## Where it would live

engine/attention.py::_compute_pressure_field — add a homeostatic_potential
pressure
psyche/state.py — expose a method that estimates the state delta of a
candidate given its content
engine/attention_config.py — weight for the new pressure

## Current state

Not started. compute_homeostatic_reward() exists and is called at end of
turn for the trace. It does not touch attention.

## Rough shape

Two possible shapes.

Shape A — state-level:
  For each candidate, ask the LLM what state change winning it would
  produce, cache the answer on the candidate, then score by the negative
  distance from setpoints of the predicted state. Expensive — one LLM
  call per candidate per turn.

Shape B — heuristic:
  For each candidate type, hardcode a rough effect. Curiosity nodes reduce
  uncertainty but increase tension. Completion candidates reduce completion
  pressure. Self-beliefs reduce coherence pressure. Coarse, cheap, no
  LLM call. Tune the direction and magnitude by hand.

Recommended starting point: Shape B, because the mechanism needs to be
seen working before it needs to be precise. If it produces useful
selection differences, upgrade to Shape A.

## References

The Modular CA architecture (TechRxiv, Feb 2026) uses this as the primary
selection signal. Constructibility as Active Inference (Zenodo, June 2026)
gives the mathematical framing: minimizing contradiction burden is
equivalent to free energy minimization.
docs/intentions/learning_progress_gated_curiosity.md
text
# Intention: Learning-Progress-Gated Curiosity

Status: seed
Created: 2026-10-04
Depends on: homeostatic_reward_as_signal

## What it is

Curiosity is currently a scalar drive. When state.curiosity > 0.6, the
VolitionEngine generates a Desire of type "understand". Simple threshold.

This intention replaces threshold-based curiosity with learning-progress
gating: curiosity should rise when the system is learning, fall when
learning plateaus, and fall further when learning fails.

## Why it matters

A threshold curiosity produces noise. It fires on anything the system
happens to be curious about, regardless of whether pursuing it is useful.

A learning-progress-gated curiosity explores the Goldilocks zone:
pursue topics where you are partly succeeding, not topics you're already
competent at (no information gain) and not topics you're failing badly at
(frustration without progress).

## Where it would live

engine/volition_engine.py::generate_desires_from_state — replace the
curiosity > 0.6 check with a computed curiosity_k value
engine/memory_consolidation.py — track per-topic prediction error trend
over turns

## Current state

Not started. Curiosity is threshold-based.

## Rough shape

curiosity_k = IG_k * g_LP(k) * g_comp(k) * g_risk(k)

where:
  IG_k     = information gain (currently could proxy as novelty)
  g_LP(k)  = sigmoid on learning progress: how much prediction error
             decreased this step
  g_comp(k)= Gaussian competence window peaking at ~0.6 success rate
  g_risk(k)= gating to zero for topics that keep producing high error

Requires tracking per-topic prediction error over multiple turns. Topic
identity can be approximated by the top curiosity graph node or the
top active thought at the time.

Simplification for first implementation: drop g_risk and g_comp, use only
IG and g_LP. Two of four terms still produces differentiated curiosity.

## References

The Modular CA architecture (TechRxiv, Feb 2026), section on
intrinsically motivated exploration.
docs/intentions/scoping_model.md
text
# Intention: Hari-Global / Participant / Session Scoping

Status: seed
Created: 2026-10-04
Depends on: migration 010

## What it is

Right now everything is scoped to session_id. Memories, curiosity nodes,
narratives, pursuits, self-beliefs, contradictions — all carry session_id
and all queries filter by it. There is no distinction between "state that
belongs to this conversation" and "state that belongs to this participant"
and "state that belongs to Hari across all participants."

The intention is to make the distinction explicit and consistent.

HARI-GLOBAL:
    constitution
    origin
    self-model
    self-beliefs
    durable interests
    world knowledge / beliefs
    long-lived curiosity

PARTICIPANT:
    relationship model
    beliefs about participant
    shared discoveries
    relational tensions

SESSION:
    episodic conversation memories
    local narrative threads
    transient working state
    conversation-specific pursuits

CYCLE:
    candidate field
    workspace
    broadcast
    action choice

TRACE:
    causal telemetry

## Why it matters

Without the distinction, two things happen. First, cross-session learning
is impossible — Hari cannot remember that this participant was the one who
asked about black holes, because relationship is session-scoped. Second,
things that should be global are accidentally session-scoped — a self-belief
formed in one session is invisible in the next.

The current default is "everything is session" because that's what was
implemented first. The default should be decided, not inherited.

## Where it would live

Every persistent model carries a scope field.
Every query filters by the appropriate scope.
Migration adds participant_id column to relevant tables and backfills.

## Current state

Migration 010 added session_id to hypotheses and contradictions. It did
not add participant_id to anything. TurnPipeline now takes a participant_id
parameter, but the only thing it affects is RelationalManager's user_id.
Self-beliefs still write with session_id. Identity model is fresh per
session.

## Rough shape

Three decisions to make before code:

1. Is self-belief Hari-global or session-scoped?
   Argument for global: a belief about herself should survive the conversation.
   Argument for session: a belief might be context-dependent.

2. Is relationship Hari-with-participant or Hari-with-session?
   Argument for participant: relationships are about people, not conversations.

3. Are narratives session-scoped or participant-scoped?
   Argument for session: a narrative about a specific conversation belongs to it.
   Argument for participant: a narrative across conversations belongs to the person.

The right answer for Hari: self-beliefs global, relationship by participant,
narratives session-scoped but able to reference participant. Not decided yet.

Migration sketch:

ALTER TABLE self_beliefs DROP COLUMN session_id;
ALTER TABLE self_beliefs ADD COLUMN scope TEXT NOT NULL DEFAULT 'hari';

ALTER TABLE relational_models ADD COLUMN participant_id TEXT;
-- (table doesn't exist yet, would need to be created)

ALTER TABLE narrative_threads ADD COLUMN participant_id TEXT;
-- narrative stays session-scoped but can reference participant
docs/intentions/identity_persistence.md
text
# Intention: Identity Persistence and Development Ledger

Status: seed
Created: 2026-10-04
Depends on: scoping_model

## What it is

IdentityModel() is constructed fresh every time a TurnPipeline is created.
Nothing writes to it. accumulated_self_narrative stays "An autonomous
cognitive entity, shaped by interaction..." forever. core_commitments
stays the three defaults. active_self_questions stays the same three.

This intention makes identity a thing that accumulates.

## Why it matters

Hari's "self" is a document that never changes. Every session she starts
as the same generic entity with the same generic commitments.

A persistent identity would let earlier sessions inform later ones. If she
formed a self-belief in a session three weeks ago, it should still be there.
If a contradiction she encountered was resolved, the resolution should
persist. If her narrative shifted, the shift should be visible.

Without this, "she has a self" is a claim about a file, not about a mind.

## Where it would live

models/identity.py — SelfModel gains a persistence path
engine/development.py — becomes the write path for identity mutations
engine/promotions.py::promote_interest_to_identity_anchor — currently
unwired, becomes the entry point for identity events
engine/generate.py::_execute_inner — reads and writes identity state
development_events table — currently empty, becomes the ledger

## Current state

The structure exists. IdentityModel, SelfModel, PerspectiveShift,
DevelopmentEvent, store_development_event, promote_interest_to_identity_anchor
all defined. Nothing calls the write paths. No identity read happens outside
build_system_prompt_from_identity, which reads the always-empty defaults.

## Rough shape

The development ledger pattern:

    experience
     ↓
    self-relevant evidence
     ↓
    self-belief candidate (proposed, not yet accepted)
     ↓
    contradiction / reinforcement against existing beliefs
     ↓
    promotion to self-belief
     ↓
    development event
     ↓
    identity reconstruction from ledger

Key principle: identity is not stored as state. It is reconstructed by
reading the ledger. This means identity changes are auditable, reversible,
and traceable to their causes.

Every DevelopmentEvent already carries source_attribution, confidence,
reason. That's enough to reconstruct why an identity change happened.

## References

models/development.py — the schema for identity mutations, currently
unused (DevelopmentEvent with event_type='identity_mutation', etc.)

models/development_event.py — the runtime form, partially wired
docs/intentions/dialogue_constitution_as_spec.md
text
# Intention: Dialogue Constitution as Living Spec

Status: seed
Created: 2026-10-04
Depends on: nothing

## What it is

There is a document — "authentic dialogue learning constitution" —
that specifies what authentic conversation looks like for Hari. It lists
principles: associative storytelling, hidden continuity, episodic cognition,
acknowledge-respond-contribute, expand-only-if-invited, story-only-if-pulled,
"stories reveal the thinker," and so on. It has concrete examples with
rejected alternatives and reasoning.

This document exists. It is not in the repository. No code points to it.

The intention is to make it a live specification: file it in the repo,
reference it from the code that implements behaviors it describes, and
build a test suite that reads it and checks whether Hari's outputs match.

## Why it matters

The constitution is a much more detailed spec than any code comment. It
has the texture of what "good conversation" looks like, with anti-patterns
and rationale. Nothing else in the repo captures that.

If it lives in a chat, it's lost. If it lives in the repo referenced from
the relevant code, it becomes a shared reference that both humans and AI
assistants can read when they touch the code that produces dialogue.

## Where it would live

docs/constitution/dialogue.md — the document itself
docs/constitution/README.md — how to read it, what "match" means
engine/generate.py::_generate_dialogue — comment referencing the doc
scripts/check_constitution.py — a script that reads a session log and
reports conformance
tests/ — a growing list of conformance tests, one per principle

## Current state

The document exists in a chat history. It is not in the repo. There is no
checking script. There is no conformance test suite.

## Rough shape

The checking script would run offline against an event log. For each
principle in the constitution, one function that reads events and returns
a score. For example:

- did-pivot-follow-association: check that when a pivot happens, the winner
  was reachable from the previous winner via graph edges
- did-story-follow-invitation: check that when a story is told, the prior
  turn contained a question or an invitation
- did-silence-follow-exhaustion: check that silence turns correlate with
  low curiosity, low completion, high rest

The constitution is not a target to optimize. It is a lens through which
to read a session and ask "does this look like what we meant." That
distinction matters — optimizing toward a spec is the failure mode we
started this whole project to avoid.

## References

The document itself, if it can be recovered from the chat.
docs/intentions/associative_field.md
text
# Intention: Multi-Domain Associative Field

Status: seed
Created: 2026-10-04
Depends on: settle_workspace telemetry fix

## What it is

The current spreading activation seeds from a single winner's content,
propagates once or twice, and offers newly-activated nodes as candidates
for the next round.

This is a chain, not a field.

The intention is to have multiple unrelated domains hot at once. If the
conversation has moved from restaurants to cars, the restaurant chain
should still be partially active in the background, and if its residual
activation peaks next turn, it should be able to win without any new
cue from the current topic.

Example: discussing food, then friend-who-broke-table, then Goa. Then
discussing cars, but background activation from the food chain is still
hot. Next turn, without any car-related cue, "Goa recommendation"
surfaces and she pivots back.

## Why it matters

This is what makes the felt texture "she has her own weather." Without
it, associations only happen one hop deep, and only when triggered by
the current topic. With it, associations can surprise — the flash that
arrives without a trigger.

## Where it would live

engine/curiosity_graph.py — the activation field already exists
(seed_from_text, step_activation, decay_activations)
engine/attention.py::load_workspace — candidates need to include
nodes whose activation is decaying from prior turns, not just freshly
spread nodes

## Current state

The activation field exists and decays over turns. But load_workspace
only pulls in nodes that were activated this turn. Nodes from prior
turns that are still above threshold are not automatically candidates.

## Rough shape

In _allocate_workspace, before building open_threads from the current
turn's candidates, also add:

    for node in graph_mgr.get_activation_landscape(threshold=0.20):
        if node was not activated this turn:
            open_threads.append({
                "id": f"residual_{node['id']}",
                "content": node["question"],
                "urgency": node["activation"],
                "item_type": "curiosity_node",
                "source": "curiosity_residual",
                "internal_source": "decaying_activation",
                ...
            })

Threshold tuning matters. Too low and everything from the last ten
turns is competing. Too high and only the most recent chain is active.
Start at 0.20 and adjust.

The mechanism is not about chain depth. It's about keeping multiple
distinct chains alive simultaneously. Chains that have not been touched
for several turns should decay to zero. Chains that have been reinforced
across a session should persist and occasionally resurface.

## References

HeLa-Mem (ACL 2026) — dual-path retrieval with Hebbian spreading.
Synapse (ACL Findings 2026) — lateral inhibition and temporal decay.
docs/intentions/pivot_measurement.md
text
# Intention: Pivot Texture Measurement

Status: seed
Created: 2026-10-04
Depends on: settle_workspace telemetry fix

## What it is

The architecture now measures whether the event was ignored. It does not
measure whether ignoring the event produced a *pivot* — a shift to content
that is unrelated to the current topic but coherent as Hari's own thread.

The intention is to add a pivot classifier that reads session traces and
reports:
- pivot rate (fraction of turns where the winner was not the event)
- pivot coherence (fraction of pivots where the winner was reachable from
  the previous winner via graph edges)
- pivot persistence (how many turns a pivot chain stays active)
- pivot surprise (fraction of pivots where the winner was not seeded by
  the current event but by residual activation)

## Why it matters

You cannot tune what you don't measure. But more importantly, you cannot
know whether the architecture is doing what you want without measuring
the shape of what it produces, not just the count of pivots.

A 50% pivot rate with every pivot incoherent is different from a 20%
pivot rate with every pivot coherent. Both are informative. Neither is
visible in the current trace columns.

## Where it would live

scripts/analyze_events.py — extend with pivot metrics
scripts/run_observatory.py — print pivot summary at end
DB view or query — for cross-session analysis

## Current state

run_observatory prints winner types but does not classify pivots.

analyze_events computes initiative from workspace composition but does
not measure whether pivots cohere or persist.

## Rough shape

Pivot classification for a turn T:
    event_was_ignored = TRUE → potential pivot
    winner_origin in {volition, curiosity_spreading, curiosity_residual,
                      internal_cognition, contradiction, pursuit}
        → confirmed pivot
    else → not a pivot (winner was a memory or narrative loaded by
        retrieval)

Coherence for turn T:
    look up winner content embedding
    look up previous turn's winner embedding
    compute cosine similarity
    if < 0.4, the pivot is incoherent
    if >= 0.4, the pivot is coherent
    (threshold approximate; tune)

Persistence for a pivot chain:
    follow turns where consecutive winners share an origin that isn't
    the event, and where content overlap exceeds threshold
    chain length in turns is the persistence

The measurement is offline. It does not affect the pipeline. It is
only for observing what the architecture does when given freedom.

## References

The dialogue constitution's "hidden continuity" principle — a pivot
feels authentic if the bridge exists in the mind even if the listener
doesn't see it.
docs/intentions/README.md
text
# Intentions

Seeds for future work. Each file captures a design that has been thought
through but not yet built. Seeds are not TODOs — they carry the intention,
the reasoning, and the shape of the implementation.

Format: see the header of any seed file.

Status values:
- seed: design captured, not started
- partial: some code exists, not wired or not complete
- ready: design is complete, implementation can begin

## Index

| Intention | Status | Depends on |
|---|---|---|
| typed_cognitive_candidate.md | seed | — |
| homeostatic_reward_as_signal.md | seed | settle_workspace telemetry fix |
| learning_progress_gated_curiosity.md | seed | homeostatic_reward_as_signal |
| scoping_model.md | seed | migration 010 |
| identity_persistence.md | seed | scoping_model |
| dialogue_constitution_as_spec.md | seed | — |
| associative_field.md | seed | settle_workspace telemetry fix |
| pivot_measurement.md | seed | settle_workspace telemetry fix |

## How to use these

Read the seed. If the design is clear enough to implement, do it. If it
needs more thought, add a "## Notes" section at the bottom of the seed
and write what you're thinking. If the design is wrong, edit the seed or
delete it and note in git why.

Seeds are living documents. They improve as more people read them and
add to them. That is the whole point.

## Relationship to the code

Where a seed has a clear insertion point, the code has a comment:

    # Seed: docs/intentions/<file>.md

Grep for "Seed:" to find all the places where the codebase points at a
future intention.