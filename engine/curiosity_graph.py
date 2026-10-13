# engine/curiosity_graph.py
"""
Curiosity Graph with Spreading Activation Field.

Persistent per-session network of curiosity nodes and edges, plus an
in-memory activation field that spreads across the network and decays
over turns.

Preserved from original:
    - session isolation
    - PostgreSQL persistence via batch upserts
    - thread-safe async lock
    - spread_activation (kept for backward compatibility)

Added:
    - activation field (_activation, decay, lateral inhibition)
    - Hebbian edge reinforcement with co-activation
    - seed_from_text for fuzzy text-to-node matching
    - activation landscape queries
"""

import json
import asyncio
import hashlib
import logging
import networkx as nx

from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from db.connection import get_pool

logger = logging.getLogger(__name__)

COACTIVATION_EDGE_DELTA = 0.05
HEBBIAN_EDGE_DECAY = 0.995
ACTIVATION_DECAY_BASE = 0.85
ACTIVATION_FLOOR = 0.01
SPREAD_DECAY = 0.5
LATERAL_INHIBITION = 0.3
CANDIDATE_THRESHOLD = 0.15
NEW_NODE_SEED_ACTIVATION = 0.3


class CuriosityGraph:
    def __init__(self):
        self.session_id: str = ""
        self._graph: Optional[nx.Graph] = None
        self._sync_task: Optional[asyncio.Task] = None
        self._sync_event: Optional[asyncio.Event] = None
        self._should_stop: bool = False
        self._lock = asyncio.Lock()
        self._activation: Dict[str, float] = {}
        self._last_decay_turn: int = 0

    async def initialize(self, session_id: str) -> None:
        self.session_id = session_id
        async with self._lock:
            self._graph = nx.Graph()
            self._sync_event = asyncio.Event()
            pool = await get_pool()
            if not pool:
                print(f"Cannot load curiosity graph for {session_id}: no pool.")
                return
            async with pool.acquire() as conn:
                nodes = await conn.fetch(
                    "SELECT id, core_question, importance, exploration_progress, properties "
                    "FROM curiosity_nodes WHERE session_id = $1",
                    session_id,
                )
                for n in nodes:
                    props = n["properties"] if isinstance(n["properties"], dict) else {}
                    self._graph.add_node(
                        n["id"],
                        core_question=n["core_question"],
                        importance=n["importance"],
                        exploration_progress=n["exploration_progress"],
                        **props
                    )
                node_ids = [node["id"] for node in nodes]
                edges = []
                if node_ids:
                    edges = await conn.fetch(
                        "SELECT source_id, target_id, weight FROM curiosity_edges "
                        "WHERE source_id = ANY($1::text[]) AND target_id = ANY($1::text[])",
                        node_ids,
                    )
                for e in edges:
                    self._graph.add_edge(e["source_id"], e["target_id"], weight=e["weight"])
            print(f"Curiosity graph [{session_id}]: {len(self._graph.nodes)} nodes, {len(self._graph.edges)} edges")

    # ------------------------------------------------------------------
    # NODE AND EDGE OPERATIONS
    # ------------------------------------------------------------------

    async def add_node(
        self,
        question: str,
        importance: float = 0.5,
        origin_trace_id: Optional[str] = None
    ) -> str:
        """Add a curiosity node. Returns node ID."""
        async with self._lock:
            if self._graph is None:
                return "error"

            clean_text = question.strip().lower()
            text_hash = hashlib.sha256(clean_text.encode("utf-8")).hexdigest()[:16]
            node_id = f"{self.session_id}_{text_hash}"

            if node_id in self._graph:
                existing_importance = self._graph.nodes[node_id].get("importance", 0)
                if importance > existing_importance:
                    self._graph.nodes[node_id]["importance"] = importance
                    self._graph.nodes[node_id]["last_trace_id"] = origin_trace_id
                    self._graph.nodes[node_id]["last_referenced"] = datetime.now(timezone.utc).isoformat()
                return node_id

            self._graph.add_node(
                node_id,
                core_question=question,
                importance=max(0.0, min(1.0, importance)),
                session_id=self.session_id,
                origin_trace_id=origin_trace_id,
                created_at=datetime.now(timezone.utc).isoformat(),
                last_referenced=datetime.now(timezone.utc).isoformat(),
                exploration_progress=0.0
            )
            # Seed new node with moderate activation so it doesn't decay immediately
            self._activation[node_id] = max(NEW_NODE_SEED_ACTIVATION, importance)
            await self._queue_sync()
            return node_id

    async def update_edge(self, node1: str, node2: str, delta: float = 0.05) -> None:
        """Create or strengthen an edge between two nodes."""
        async with self._lock:
            if self._graph is None:
                return
            if self._graph.has_edge(node1, node2):
                current = float(self._graph[node1][node2].get("weight", 0.0))
                self._graph[node1][node2]["weight"] = min(1.0, current + delta)
            else:
                self._graph.add_edge(node1, node2, weight=max(0.0, min(1.0, delta)))
            await self._queue_sync()

    def reinforce_edge(self, node_a: str, node_b: str, delta: float = 0.03) -> None:
        """Synchronous Hebbian reinforcement. Used during activation spreading."""
        if self._graph is None:
            return
        if node_a not in self._graph or node_b not in self._graph:
            return
        if self._graph.has_edge(node_a, node_b):
            current = float(self._graph[node_a][node_b].get("weight", 0.0))
            self._graph[node_a][node_b]["weight"] = min(1.0, current + delta)
        else:
            self._graph.add_edge(node_a, node_b, weight=delta)
        if self._sync_event:
            self._sync_event.set()

    def reinforce_coactive(self, threshold: float = 0.3) -> None:
        """Reinforce edges between all nodes currently active above threshold."""
        if self._graph is None:
            return
        active = [
            nid for nid, act in self._activation.items()
            if act >= threshold and nid in self._graph
        ]
        for i, a in enumerate(active):
            for b in active[i + 1:]:
                self.reinforce_edge(a, b, delta=0.03)

    async def observe_workspace(self, workspace_items: List[Any]) -> None:
        """Learn co-activation edges from workspace composition."""
        curiosity_ids = set()
        for item in workspace_items:
            if not hasattr(item, "item_type") or not hasattr(item, "payload"):
                continue
            if item.item_type == "curiosity_node":
                node_id = item.payload.get("id")
                if node_id:
                    curiosity_ids.add(node_id)

        if len(curiosity_ids) >= 2:
            node_list = list(curiosity_ids)
            for i in range(len(node_list)):
                for j in range(i + 1, len(node_list)):
                    await self.update_edge(node_list[i], node_list[j], delta=COACTIVATION_EDGE_DELTA)

    async def get_top_nodes(self, limit: int = 5) -> List[Dict[str, Any]]:
        async with self._lock:
            if self._graph is None:
                return []
            nodes = [(n, data.get("importance", 0)) for n, data in self._graph.nodes(data=True)]
            nodes.sort(key=lambda x: x[1], reverse=True)
            return [
                {"id": n, "question": data.get("core_question", n), "importance": imp}
                for n, imp in nodes[:limit]
            ]

    # ------------------------------------------------------------------
    # ACTIVATION FIELD
    # ------------------------------------------------------------------

    def seed_activation(self, node_id: str, weight: float = 1.0) -> None:
        """Add activation to a specific node."""
        if self._graph is None or node_id not in self._graph:
            return
        current = self._activation.get(node_id, 0.0)
        self._activation[node_id] = min(1.0, current + weight)

    def seed_from_text(self, text: str, weight: float = 1.0) -> List[str]:
        """
        Fuzzy seed activation from a text string.
        Matches against node questions by token overlap.
        Returns list of matched node IDs.
        """
        if self._graph is None or not text:
            return []
        clean = text.strip().lower()

        # Try exact hash match first
        text_hash = hashlib.sha256(clean.encode("utf-8")).hexdigest()[:16]
        exact_id = f"{self.session_id}_{text_hash}"
        matched: List[str] = []
        if exact_id in self._graph:
            self.seed_activation(exact_id, weight)
            matched.append(exact_id)

        # Fuzzy token match
        tokens = [t for t in clean.split() if len(t) > 3]
        if not tokens:
            return matched
        for node_id, data in self._graph.nodes(data=True):
            if node_id in matched:
                continue
            question = str(data.get("core_question", "")).lower()
            hits = sum(1 for t in tokens[:6] if t in question)
            if hits >= 1:
                boost = weight * (0.4 + 0.15 * hits)
                self.seed_activation(node_id, boost)
                matched.append(node_id)
        return matched

    def activate(
        self,
        seeds: List[str],
        depth: int = 2,
        decay: float = SPREAD_DECAY,
        threshold: float = CANDIDATE_THRESHOLD,
        lateral_inhibition: float = LATERAL_INHIBITION,
    ) -> Dict[str, float]:
        """
        Spread activation from seeds. Applies lateral inhibition:
        nodes below max_activation * lateral_inhibition are dropped.
        Returns the delta applied this step.
        """
        if self._graph is None:
            return {}

        # Resolve seeds to node IDs
        seed_nodes: List[str] = []
        for seed in seeds:
            if seed in self._graph:
                seed_nodes.append(seed)
                continue
            clean = seed.strip().lower()
            h = hashlib.sha256(clean.encode()).hexdigest()[:16]
            candidate = f"{self.session_id}_{h}"
            if candidate in self._graph:
                seed_nodes.append(candidate)
        if not seed_nodes:
            return {}

        delta: Dict[str, float] = {s: 1.0 for s in seed_nodes}
        frontier = {s: 1.0 for s in seed_nodes}

        for _ in range(depth):
            next_frontier: Dict[str, float] = {}
            for node_id, parent_activation in frontier.items():
                if node_id not in self._graph:
                    continue
                for neighbor in self._graph.neighbors(node_id):
                    edge_weight = float(self._graph[node_id][neighbor].get("weight", 0.1))
                    child = parent_activation * edge_weight * decay
                    if child <= 0.0:
                        continue
                    prev = delta.get(neighbor, 0.0)
                    if child > prev:
                        delta[neighbor] = child
                        next_frontier[neighbor] = child
            frontier = next_frontier

        # Lateral inhibition
        if delta:
            max_act = max(delta.values())
            for node_id in list(delta.keys()):
                if delta[node_id] < max_act * lateral_inhibition:
                    del delta[node_id]

        # Apply delta
        for node_id, add in delta.items():
            self._activation[node_id] = self._activation.get(node_id, 0.0) + add

        return delta

    def step_activation(self) -> List[Dict[str, Any]]:
        """
        One propagation step from the current activation field.
        Unlike activate(), this uses existing _activation as source.
        Returns nodes that crossed the candidate threshold.
        """
        if self._graph is None or not self._activation:
            return []

        next_activations: Dict[str, float] = {}
        for node_id, activation in self._activation.items():
            if node_id not in self._graph:
                continue
            for neighbor in self._graph.neighbors(node_id):
                edge_weight = float(self._graph[node_id][neighbor].get("weight", 0.1))
                spread = activation * edge_weight * SPREAD_DECAY
                if spread < ACTIVATION_FLOOR:
                    continue
                current = next_activations.get(neighbor, 0.0)
                next_activations[neighbor] = min(1.0, current + spread)

        for node_id, activation in next_activations.items():
            current = self._activation.get(node_id, 0.0)
            self._activation[node_id] = min(1.0, current + activation)

        return self.get_activation_landscape(threshold=CANDIDATE_THRESHOLD)

    def decay_activations(self, current_turn: int, base_rate: float = ACTIVATION_DECAY_BASE) -> None:
        """Decay activations based on turns elapsed since last decay."""
        if current_turn <= self._last_decay_turn:
            return
        turns_elapsed = current_turn - self._last_decay_turn
        factor = base_rate ** turns_elapsed
        for node_id in list(self._activation.keys()):
            self._activation[node_id] *= factor
            if self._activation[node_id] < ACTIVATION_FLOOR:
                del self._activation[node_id]
        self._last_decay_turn = current_turn

    def get_activation_landscape(self, threshold: float = CANDIDATE_THRESHOLD) -> List[Dict[str, Any]]:
        """Return all nodes above threshold, sorted by activation."""
        results = []
        if self._graph is None:
            return results
        for node_id, activation in self._activation.items():
            if activation < threshold:
                continue
            if node_id not in self._graph:
                continue
            data = self._graph.nodes[node_id]
            results.append({
                "id": node_id,
                "question": data.get("core_question", node_id),
                "importance": float(data.get("importance", 0.5)),
                "activation": float(activation),
                "session_id": data.get("session_id"),
            })
        results.sort(key=lambda r: r["activation"], reverse=True)
        return results

    def get_primed_nodes(self, threshold: float = 0.4) -> List[Dict[str, Any]]:
        """Return nodes above the priming threshold (conscious access)."""
        return [n for n in self.get_activation_landscape(threshold) if n["activation"] >= threshold]

    def activation_snapshot(self) -> Dict[str, float]:
        """Diagnostic access to the current activation field."""
        return dict(self._activation)

    # ------------------------------------------------------------------
    # BACKWARD COMPATIBILITY
    # ------------------------------------------------------------------

    async def spread_activation(
        self, seed_ids: List[str], depth: int = 2, decay: float = 0.5, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Original API preserved. Returns activated nodes without persisting
        to _activation. For callers that just want a one-shot propagation.
        """
        async with self._lock:
            if self._graph is None:
                return []
            activated: Dict[str, float] = {}
            frontier: Dict[str, float] = {}
            for seed_id in seed_ids:
                if seed_id in self._graph:
                    activated[seed_id] = 1.0
                    frontier[seed_id] = 1.0
            for _ in range(depth):
                if not frontier:
                    break
                next_frontier: Dict[str, float] = {}
                for node_id, parent_activation in frontier.items():
                    if node_id not in self._graph:
                        continue
                    for neighbor in self._graph.neighbors(node_id):
                        edge_weight = float(self._graph[node_id][neighbor].get("weight", 0.1))
                        child_activation = parent_activation * edge_weight * decay
                        if child_activation <= 0.0:
                            continue
                        previous = activated.get(neighbor, 0.0)
                        if child_activation > previous:
                            activated[neighbor] = child_activation
                            next_frontier[neighbor] = child_activation
                frontier = next_frontier
            results = []
            seed_set = set(seed_ids)
            for node_id, activation in activated.items():
                if node_id in seed_set:
                    continue
                node_data = self._graph.nodes[node_id]
                results.append({
                    "id": node_id,
                    "question": node_data.get("core_question", node_id),
                    "importance": float(node_data.get("importance", 0.5)),
                    "activation": float(activation),
                    "session_id": node_data.get("session_id"),
                })
            results.sort(key=lambda item: item["activation"], reverse=True)
            return results[:limit]

    # ------------------------------------------------------------------
    # DECAY
    # ------------------------------------------------------------------

    async def decay(self, decay_factor: float = 0.99) -> None:
        """Decay importance weights and edge weights. Apply edge-level Hebbian decay."""
        async with self._lock:
            if self._graph is None:
                return
            for node, data in self._graph.nodes(data=True):
                data["importance"] *= decay_factor
            for u, v in self._graph.edges():
                current = float(self._graph[u][v].get("weight", 0.0))
                self._graph[u][v]["weight"] = current * HEBBIAN_EDGE_DECAY
        await self._queue_sync()

    # ------------------------------------------------------------------
    # SYNC
    # ------------------------------------------------------------------

    async def _queue_sync(self) -> None:
        if self._sync_event:
            self._sync_event.set()

    async def start_sync_worker(self, interval: int = 60) -> None:
        if self._sync_task is not None and not self._sync_task.done():
            return
        self._should_stop = False
        self._sync_task = asyncio.create_task(self._sync_loop(interval))

    async def stop_sync_worker(self) -> None:
        self._should_stop = True
        if self._sync_event:
            self._sync_event.set()
        if self._sync_task:
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass
        await self._sync_now()

    async def _sync_loop(self, interval: int) -> None:
        try:
            while not self._should_stop:
                try:
                    if self._sync_event:
                        await asyncio.wait_for(self._sync_event.wait(), timeout=interval)
                except asyncio.TimeoutError:
                    pass
                await self._sync_now()
                if self._sync_event and self._sync_event.is_set():
                    self._sync_event.clear()
        except asyncio.CancelledError:
            await self._sync_now()
            raise

    async def _sync_now(self) -> None:
        async with self._lock:
            if self._graph is None or len(self._graph.nodes) == 0:
                return
            pool = await get_pool()
            if not pool:
                return

            node_ids, questions, importances, progresses, properties_json = [], [], [], [], []
            for node, data in self._graph.nodes(data=True):
                node_ids.append(node)
                questions.append(data.get("core_question", node))
                importances.append(float(data.get("importance", 0.5)))
                progresses.append(float(data.get("exploration_progress", 0.0)))
                props = {k: v for k, v in data.items()
                         if k not in ["core_question", "importance", "exploration_progress"]}
                properties_json.append(json.dumps(props))

            edge_sources, edge_targets, edge_weights = [], [], []
            for u, v, data in self._graph.edges(data=True):
                edge_sources.append(u)
                edge_targets.append(v)
                edge_weights.append(float(data.get("weight", 0.0)))

            async with pool.acquire() as conn:
                async with conn.transaction():
                    if node_ids:
                        session_ids = [self.session_id] * len(node_ids)
                        await conn.execute("""
                            INSERT INTO curiosity_nodes (id, core_question, importance, exploration_progress, properties, session_id)
                            SELECT * FROM UNNEST($1::TEXT[], $2::TEXT[], $3::FLOAT[], $4::FLOAT[], $5::JSONB[], $6::TEXT[])
                            ON CONFLICT (id) DO UPDATE
                            SET core_question = EXCLUDED.core_question,
                                importance = EXCLUDED.importance,
                                exploration_progress = EXCLUDED.exploration_progress,
                                last_referenced = NOW(),
                                properties = EXCLUDED.properties,
                                session_id = EXCLUDED.session_id
                            """, node_ids, questions, importances, progresses, properties_json, session_ids)

                    if edge_sources:
                        await conn.execute("""
                            INSERT INTO curiosity_edges (source_id, target_id, weight)
                            SELECT * FROM UNNEST($1::TEXT[], $2::TEXT[], $3::FLOAT[])
                            ON CONFLICT (source_id, target_id) DO UPDATE
                            SET weight = EXCLUDED.weight
                        """, edge_sources, edge_targets, edge_weights)


_graph_managers: Dict[str, CuriosityGraph] = {}


async def get_graph_manager(session_id: str) -> CuriosityGraph:
    """Return a curiosity graph isolated to one session."""
    if session_id not in _graph_managers:
        graph = CuriosityGraph()
        await graph.initialize(session_id)
        try:
            await graph.start_sync_worker(interval=30)
        except Exception as e:
            logger.warning(f"Curiosity graph sync worker failed to start: {e}")
        _graph_managers[session_id] = graph
    return _graph_managers[session_id]


async def close_session_graph(session_id: str) -> None:
    """Clean up a session's graph."""
    graph = _graph_managers.pop(session_id, None)
    if graph is not None:
        try:
            await graph.stop_sync_worker()
        except Exception:
            pass