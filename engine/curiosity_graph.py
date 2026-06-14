# hari/engine/curiosity_graph.py
"""
Phase 4: Curiosity Graph – High-performance, persistent graph storage using PostgreSQL.
Optimized with multi-row batch upserts, thread‑safe lock, and strict async patterns.
"""

import json
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

import networkx as nx
from db.connection import get_pool


class CuriosityGraph:
    def __init__(self):
        self._graph: Optional[nx.Graph] = None
        self._sync_task: Optional[asyncio.Task] = None
        self._sync_event: Optional[asyncio.Event] = None
        self._should_stop: bool = False
        self._lock = asyncio.Lock()          # <-- ADDED: protects all graph operations

    async def initialize(self) -> None:
        async with self._lock:
            self._graph = nx.Graph()
            self._sync_event = asyncio.Event()
            pool = await get_pool()
            if not pool:
                print("⚠️ Cannot load curiosity graph: No active database pool.")
                return
            async with pool.acquire() as conn:
                nodes = await conn.fetch("SELECT id, core_question, importance, exploration_progress, properties FROM curiosity_nodes")
                for n in nodes:
                    props = n["properties"] if isinstance(n["properties"], dict) else {}
                    self._graph.add_node(
                        n["id"],
                        core_question=n["core_question"],
                        importance=n["importance"],
                        exploration_progress=n["exploration_progress"],
                        **props
                    )
                edges = await conn.fetch("SELECT source_id, target_id, weight FROM curiosity_edges")
                for e in edges:
                    self._graph.add_edge(e["source_id"], e["target_id"], weight=e["weight"])
            print(f"🧠 Curiosity graph loaded: {len(self._graph.nodes)} nodes, {len(self._graph.edges)} edges")

    async def add_node(self, question: str, importance: float = 0.5) -> None:
        async with self._lock:
            if self._graph is None:
                return
            node_id = question.lower().strip().replace(" ", "_")
            self._graph.add_node(
                node_id,
                core_question=question,
                importance=importance,
                exploration_progress=0.0,
                last_referenced=datetime.now(timezone.utc).isoformat()
            )
        await self._queue_sync()

    async def update_edge(self, node1: str, node2: str, delta: float = 0.05) -> None:
        async with self._lock:
            if self._graph is None:
                return
            n1 = node1.lower().strip().replace(" ", "_")
            n2 = node2.lower().strip().replace(" ", "_")
            if self._graph.has_edge(n1, n2):
                current = self._graph[n1][n2].get("weight", 0.0)
                self._graph[n1][n2]["weight"] = min(1.0, current + delta)
            else:
                self._graph.add_edge(n1, n2, weight=delta)
        await self._queue_sync()

    async def get_top_nodes(self, limit: int = 5) -> List[Dict[str, Any]]:
        async with self._lock:
            if self._graph is None:
                return []
            nodes = [(n, data.get("importance", 0)) for n, data in self._graph.nodes(data=True)]
            nodes.sort(key=lambda x: x[1], reverse=True)
            return [{"id": n, "question": data.get("core_question", n), "importance": imp} for n, imp in nodes[:limit]]

    async def decay(self, decay_factor: float = 0.99) -> None:
        async with self._lock:
            if self._graph is None:
                return
            for node, data in self._graph.nodes(data=True):
                data["importance"] *= decay_factor
            for u, v in self._graph.edges():
                self._graph[u][v]["weight"] *= decay_factor
        await self._queue_sync()

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
        await self._sync_now()  # Final flush

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
            # Prepare batch payloads
            node_ids, questions, importances, progresses, properties_json = [], [], [], [], []
            for node, data in self._graph.nodes(data=True):
                node_ids.append(node)
                questions.append(data.get("core_question", node))
                importances.append(float(data.get("importance", 0.5)))
                progresses.append(float(data.get("exploration_progress", 0.0)))
                props = {k: v for k, v in data.items() if k not in ["core_question", "importance", "exploration_progress"]}
                properties_json.append(json.dumps(props))
            edge_sources, edge_targets, edge_weights = [], [], []
            for u, v, data in self._graph.edges(data=True):
                edge_sources.append(u)
                edge_targets.append(v)
                edge_weights.append(float(data.get("weight", 0.0)))

            async with pool.acquire() as conn:
                async with conn.transaction():
                    if node_ids:
                        # Fixed batch insertion – generate timestamps array of correct length
                        timestamps = [datetime.now(timezone.utc)] * len(node_ids)
                        await conn.execute("""
                            INSERT INTO curiosity_nodes (id, core_question, importance, exploration_progress, last_referenced, properties)
                            SELECT * FROM UNNEST($1::TEXT[], $2::TEXT[], $3::FLOAT[], $4::FLOAT[], $5::TIMESTAMP[], $6::JSONB[])
                            ON CONFLICT (id) DO UPDATE
                            SET core_question = EXCLUDED.core_question,
                                importance = EXCLUDED.importance,
                                exploration_progress = EXCLUDED.exploration_progress,
                                last_referenced = NOW(),
                                properties = EXCLUDED.properties
                        """, node_ids, questions, importances, progresses, timestamps, properties_json)

                    if edge_sources:
                        await conn.execute("""
                            INSERT INTO curiosity_edges (source_id, target_id, weight)
                            SELECT * FROM UNNEST($1::TEXT[], $2::TEXT[], $3::FLOAT[])
                            ON CONFLICT (source_id, target_id) DO UPDATE
                            SET weight = EXCLUDED.weight
                        """, edge_sources, edge_targets, edge_weights)


_graph_manager: Optional[CuriosityGraph] = None

async def get_graph_manager() -> CuriosityGraph:
    global _graph_manager
    if _graph_manager is None:
        _graph_manager = CuriosityGraph()
        await _graph_manager.initialize()
    return _graph_manager