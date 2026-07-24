# Hari State Specification

**Version:** 1.0
**Last Updated:** 2026-07-20
**Status:** Draft — To Be Finalized

---

## 1. Unified State Object

The entire cognitive state of Hari is represented by a unified object:

```python
class HariState:
    # ===== Persistent (changes slowly, through consolidation/identity events) =====
    identity: IdentityModel
    relationships: RelationshipModel
    long_term_memory: List[MemoryEvent]
    
    # ===== Dynamic (changes every turn) =====
    workspace: List[WorkspaceItem]
    
    # Homeostatic drives (0.0 to 1.0)
    drives: Dict[str, float] = {
        "care": 0.5,
        "curiosity": 0.5,
        "completion": 0.5,
        "coherence": 0.5,
        "maintenance": 0.5,
        "rest": 0.2,
        "novelty": 0.5
    }
    
    # Affective VAD (-1.0 to +1.0)
    affect: Dict[str, float] = {
        "valence": 0.0,
        "arousal": 0.0,
        "dominance": 0.0
    }
    
    # Conversational (0.0 to 1.0)
    conversational: Dict[str, float] = {
        "momentum": 0.5,
        "stability": 0.5,
        "engagement": 0.5
    }
    
    # Meta-cognitive (0.0 to 1.0)
    meta_cognitive: Dict[str, float] = {
        "uncertainty": 0.0,
        "social_ambiguity": 0.0,
        "cognitive_tension": 0.0,
        "presence": 0.0
    }
    
    # ===== Expression (changes based on interaction state) =====
    expression_policy: ExpressionPolicy
    interaction_state: InteractionState
2. State Topology
Persistent State (Changes Only Through Explicit Events)
Component	Update Mechanism	Example Triggers
Identity	Perspective shifts, development events	Contradiction resolution, identity mutation
Relationships	Landmarks, trust/familiarity updates	Repeated interaction, trust violation
Long-term Memory	Consolidation, forgetting	Retrieval reinforcement, decay
Dynamic State (Changes Every Turn)
Component	Update Mechanism	Example Triggers
Workspace	Competition, broadcast	Every turn
Drives	Asymptotic updates, natural drift	Every turn
Affect	Asymptotic updates, cascades	Every turn
Conversational	State updates	Every turn
Meta-cognitive	State updates	Every turn
Expression State (Derived from Dynamic + Interaction)
Component	Update Mechanism	Example Triggers
Interaction State	Perturbation analysis	Every external input
Expression Policy	State evaluation	Before generating response
3. Time Model
Primary Time: Turns
The basic unit of time is a conversation turn.

Every turn processes input and updates state.

Secondary Time: Consolidation Cycles
Every N turns (default: 10), consolidation runs:

Memory decay

Relationship decay

Hypothesis promotion

Tertiary Time: Idle Processing
When no input arrives for M turns (default: 5), Hari enters idle processing:

Continues natural drift

May generate internal hypotheses

May revisit old memories

State Update Frequency
Component	Update Frequency
Workspace	Every turn
Drives	Every turn (asymptotic)
Affect	Every turn (asymptotic)
Memory	Every turn (retrieval), Every cycle (decay)
Relationships	Every turn (delta), Every cycle (decay)
Identity	Rare (development events)
4. Process vs. State Separation
Concept	State (What Is)	Process (What Happens)
Memory	Stored memory events	Retrieval, storage, consolidation, forgetting
Curiosity	Curiosity drive value	Exploration, question generation
Relationship	Trust, familiarity values	Update on interaction, decay on inactivity
Trajectory	Current topic/thread	Deviation detection, thread switching
Economy	Economy pressure	Brevity decision, resource allocation
5. Identity Evolution Rules
Immutable (Never Changes)
Constitution (existential_mode, asymmetry_law, integrity_anchor)

Origin (creator_name, creation_story, architecture_summary)

Slowly Evolving (Changes Through Development Events)
Self-narrative (accumulated_self_narrative)

Core commitments

Active self-questions

Identity stability score

Conditions for Change
DevelopmentEvent of type identity_mutation or paradigm_shift

Accumulation of significant PerspectiveShifts

Identity stability score must be above threshold (0.7+)

6. Optimization Targets (Drives, Not Single Objective)
Intrinsic Drives (To Be Maintained)
Drive	Definition	Bounds
Coherence	Internal consistency	[0, 1]
Stability	Resistance to chaotic change	[0, 1]
Novelty	Capacity for new structure	[0, 1]
Prediction Accuracy	Fit with observed patterns	[0, 1]
Identity Consistency	Alignment with self-model	[0, 1]
Energy Efficiency	Resource use vs. value gained	[0, 1]
Conflicts Between Drives
Conflict	Resolution Rule
Novelty vs. Stability	Novelty cannot reduce stability below 0.3
Coherence vs. Energy	Coherence takes priority in high-uncertainty states
Prediction vs. Identity	Identity anchors take priority
7. Emergence Criteria
What Counts as "Morphogenesis"?
Pattern Formation: A recurring internal abstraction that wasn't explicitly designed.

Primitive Synchronization: Two or more primitives develop correlated behavior.

Long-term Tendencies: New dispositions that persist across sessions.

When to Flag Emergence
Recurring pattern observed in Behavior Lab

Correlation between primitives not explained by shared inputs

New behavior not attributable to any single primitive

8. Naming Ontology
Principles
Names should reflect what the concept is, not what it sounds like.

Avoid using cognitive words for engineering decisions.

Be precise: "Economy" vs. "Resource Allocation" means different things.

Current Naming
Name	Meaning	Status
Economy	Internal resource allocation pressure	Acceptable
Care	Cognitive importance attributed to other mind	Acceptable
Curiosity	Pressure toward unknowns	Acceptable
Presence	Ability to "be" without performing	Acceptable
Trajectory Deviation	Measure of conversation thread departure	Acceptable
9. The Autonomous Existence Litmus Test
The Question
If Hari never speaks again, would she still become someone different over time?

What This Tests
Is cognition driven by internal state, or by language?

Is Hari's "self" continuous without external input?

Is language a downstream effect, or the primary driver?

Evaluation Criteria
After 100 turns of silence:

Does memory continue to consolidate?

Does curiosity generate new questions?

Does relationship drift occur?

Does identity evolve?

Does economy adjust?

Success Condition
Hari's internal state evolves even without external input.

10. Primitive Contracts
Contract Structure
python
class PrimitiveContract:
    name: str
    inputs: Dict[str, Type]
    outputs: Dict[str, Type]
    state_owned: List[str]  # What state does this primitive own?
    state_read: List[str]   # What state does this primitive read?
    invariants: List[str]   # What must always be true?
    failure_modes: List[str] # What can go wrong?
    update_rule: str        # How does it update?
Example: Economy
python
EconomyContract = {
    "name": "Economy",
    "inputs": {
        "rest": "float (0-1)",
        "engagement": "float (0-1)"
    },
    "outputs": {
        "economy_pressure": "float (0-1)"
    },
    "state_owned": ["economy_pressure"],
    "state_read": ["rest", "engagement"],
    "invariants": [
        "economy_pressure >= 0.0",
        "economy_pressure <= 1.0"
    ],
    "failure_modes": [
        "Too high → verbose suppression",
        "Too low → no brevity pressure"
    ],
    "update_rule": "rest_excess = max(0.0, rest - 0.4); disengagement_excess = max(0.0, (1.0 - engagement) - 0.5); economy_pressure = min(1.0, (rest_excess + disengagement_excess) / 1.1)"
}
11. Time Specification
What "Continuous" Means
Continuous cognition: The system is always processing, not just when input arrives.

Idle state: When no input, Hari continues consolidating, decaying, and potentially generating.

State persistence: State does not reset between turns.

Scheduling
Activity	Frequency	Priority
Workspace competition	Every turn	High
Natural drift	Every turn	High
State updates	Every turn	High
Memory retrieval	Every turn	High
Consolidation	Every 10 turns	Medium
Relationship decay	Every 10 turns	Medium
Idle generation	After 5 idle turns	Low