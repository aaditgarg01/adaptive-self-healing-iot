"""Gateway observer: trusts only received readings, ages and declared positions."""

import math
import time
from simulator.models import Observation, NodeState
from simulator.network.topology import Topology
from simulator.trust.engine import TrustEngine


class LiveObserver:
    def __init__(self, store):
        self.store = store
        self.latest = {}
        self.seen_at = {}
        self.last_uptime = {}
        self.retired = {}
        self.last_tick = 0.0
        self.topology = Topology({}, {}, {})
        self.engine = TrustEngine(self.topology)
        for node, x, y in store.nodes():
            self.register(node, x, y, persist=False)

    def register(self, node, x, y, persist=True):
        if persist:
            self.store.register(node, x, y)
        key = int(node[1:])
        self.topology.positions[key] = (x, y)
        self.topology.neighbors = {
            i: [
                j
                for j, q in self.topology.positions.items()
                if i != j and math.dist(p, q) <= 1.5
            ]
            for i, p in self.topology.positions.items()
        }
        self.engine.states.setdefault(key, NodeState())

    def ingest(self, payload):
        node = payload["node_id"]
        key = int(node[1:])
        if key not in self.engine.states:
            raise ValueError("register node before ingestion")
        prev = self.latest.get(key)
        boot = payload["boot_id"]
        if boot in self.retired.get(key, set()):
            raise ValueError("retired boot session")
        if prev and boot == prev["boot_id"] and payload["sequence"] <= prev["sequence"]:
            return False
        if (
            prev
            and boot == prev["boot_id"]
            and payload["uptime_ms"] < prev["uptime_ms"]
        ):
            raise ValueError("uptime moved backwards")
        now = time.time()
        if not self.store.ingest(payload, now):
            return False
        if prev and boot != prev["boot_id"]:
            self.retired.setdefault(key, set()).add(prev["boot_id"])
        self.latest[key] = payload
        self.seen_at[key] = time.monotonic()
        return True

    def tick(self):
        now = time.monotonic()
        if now - self.last_tick < 2:
            return
        self.last_tick = now
        observations = []
        for key in self.engine.states:
            payload = self.latest.get(key)
            fresh = payload is not None and now - self.seen_at[key] <= 3.0
            # Arrival age is observable; it is NOT one-way network latency.
            observations.append(
                Observation(
                    key,
                    payload["temperature"] if fresh else None,
                    payload["humidity"] if fresh else None,
                    fresh,
                    0.0 if fresh else None,
                    payload["sensor_ok"] if fresh else True,
                )
            )
        self.engine.update(observations, time.time())

    def snapshot(self):
        return {
            "nodes": [
                {
                    "node_id": f"N{i:02}",
                    "sensing_trust": s.sensing.score,
                    "communication_trust": s.communication.score,
                    "status": s.status,
                    "reason": s.reason,
                    "telemetry": self.latest.get(i),
                }
                for i, s in self.engine.states.items()
            ],
            "events": self.engine.events,
            "limitation": "Live communication trust measures freshness, not unsynchronized one-way latency. Restart resets trust; stored telemetry remains.",
        }
