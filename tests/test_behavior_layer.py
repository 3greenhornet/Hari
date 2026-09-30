import pytest

from engine.behavior import select_behavior, BehaviorDecision
from engine.reflexion_controller import ReflexionController
from engine.curiosity_graph import CuriosityGraph
from psyche.state import HariState
from engine.attention import WorkspaceItem


@pytest.mark.asyncio
async def test_curiosity_spread_activation_returns_influenced_neighbors():
    graph = CuriosityGraph()
    graph._graph = __import__("networkx").Graph()
    graph._graph.add_edge("a", "b", weight=0.8)
    graph._graph.add_edge("b", "c", weight=0.5)
    graph._graph.nodes["a"].update({"core_question": "seed", "importance": 1.0})
    graph._graph.nodes["b"].update({"core_question": "middle", "importance": 0.5})
    graph._graph.nodes["c"].update({"core_question": "leaf", "importance": 0.2})

    results = await graph.spread_activation(["a"], depth=2, decay=0.5, limit=10)
    assert any(item["id"] == "c" for item in results)
    assert all(item["activation"] > 0 for item in results)


def test_select_behavior_returns_default_when_no_winner():
    decision = select_behavior(None, HariState())
    assert decision.mode == "hold"
    assert decision.source == "none"


def test_select_behavior_prioritizes_boundary_resolution():
    winner = WorkspaceItem(
        id="w1",
        item_type="memory",
        source="volition",
        payload={"source": "volition", "urgency": 0.9, "internal_source": "assert_boundary"},
    )
    decision = select_behavior(winner, HariState())
    assert decision.mode == "redirect"
    assert decision.source == "volition"


def test_reflexion_controller_updates_state_on_prediction_failure():
    state = HariState()
    controller = ReflexionController(g_threshold=0.8, gamma=0.25)
    result = controller.process_prediction_failure(state, prediction_error=0.9)
    assert result["workspace_weight"] > 1.0
    assert state.arousal >= 0.0
    assert state.cognitive_tension >= 0.0
