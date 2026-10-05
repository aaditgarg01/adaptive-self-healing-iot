from dataclasses import asdict
import heapq
import time
from simulator.models import Config, Observation
from simulator.network.topology import Topology
from simulator.trust.engine import TrustEngine
from simulator.routing.router import route, all_routes
from simulator.faults.world import World


class Simulation:
    def __init__(self, config=Config()):
        self.config = config
        self.topology = Topology.grid(
            config.nodes, config.communication_radius, config.sensing_radius
        )
        self.engine = TrustEngine(
            self.topology, config.method, config.context, config.recovery
        )
        self.world = World(config, self.topology)
        self.step_index = 0
        self.probes, self.packets = [], []
        self.serial = 0
        self.routes = {}
        self.busy_until = {}
        self.history = []
        self.timeline = []
        self.metrics = {
            k: 0
            for k in (
                "generated",
                "delivered",
                "accepted",
                "correct",
                "data_attempts",
                "control_packets",
                "route_changes",
                "tp",
                "tn",
                "fp",
                "fn",
                "available_node_steps",
                "total_node_steps",
                "event_false_isolations",
                "event_node_steps",
            )
        }
        self.delivery_latency = []
        self.first_detection, self.first_recovery, self.fault_onsets = {}, {}, {}
        self.ever_faulty = set()
        self.ever_quarantined = set()
        self.compute_seconds = 0.0
        self.overrides = (
            {}
        )  # Used only by interactive fault injection, never benchmark runs.

    def inject(self, node, mode):
        if node not in self.engine.states:
            raise ValueError("unknown node")
        if mode not in (
            "none",
            "sensor_bias",
            "noise",
            "packet_loss",
            "high_latency",
            "node_failure",
            "intermittent",
        ):
            raise ValueError("unknown fault")
        self.overrides[node] = mode
        self.timeline.append(
            {
                "time": self.step_index * self.config.interval_s,
                "node_id": node,
                "kind": "injection",
                "message": f"Operator requested {mode}",
            }
        )

    def step(self):
        if self.step_index >= self.config.steps:
            return self.snapshot()
        start_clock = time.perf_counter()
        step, dt = self.step_index, self.config.interval_s
        now, end = step * dt, (step + 1) * dt
        truth = {i: self.world.truth(step, i) for i in self.engine.states}
        if self.overrides:
            from dataclasses import replace

            for i, mode in self.overrides.items():
                # Manual intermittent faults alternate on the same eight-step cadence.
                if mode == "intermittent" and (step // 8) % 2:
                    mode = "none"
                v = truth[i]
                sense = mode in ("sensor_bias", "noise", "intermittent")
                temp = v.temperature + (
                    15
                    if mode in ("sensor_bias", "intermittent")
                    else (
                        (self.world.uniform(step, i, "manual") - 0.5) * 24
                        if mode == "noise"
                        else 0
                    )
                )
                truth[i] = replace(
                    v,
                    fault=mode,
                    sensing_fault=sense,
                    communication_fault=mode
                    in ("packet_loss", "high_latency", "node_failure"),
                    reported_temperature=temp,
                )
        # A separate, explicitly costed management channel keeps quarantine observable.
        for i, v in truth.items():
            success, latency = self.world.transmission(
                step, i, i, 0, 0, truth, diagnostic=True
            )
            self.metrics["control_packets"] += 1 + int(success)
            if success:
                self.serial += 1
                heapq.heappush(
                    self.probes,
                    (
                        now + latency / 1000,
                        self.serial,
                        Observation(
                            i, v.reported_temperature, v.humidity, True, latency
                        ),
                    ),
                )
        observations = {i: Observation(i, None, None, False, None) for i in truth}
        while self.probes and self.probes[0][0] <= end:
            _, _, obs = heapq.heappop(self.probes)
            observations[obs.node_id] = obs
        previous_event_count = len(self.engine.events)
        self.engine.update(list(observations.values()), end)
        self.timeline.extend(self.engine.events[previous_event_count:])
        route_table = all_routes(self.topology, self.engine.states, self.config.method)
        for i, v in truth.items():
            state = self.engine.states[i]
            actual = v.sensing_fault or v.communication_fault
            detected = state.status in ("suspicious", "isolated", "recovering")
            self.metrics[
                (
                    "tp"
                    if actual and detected
                    else "fn" if actual else "fp" if detected else "tn"
                )
            ] += 1
            if actual:
                self.ever_faulty.add(i)
                self.fault_onsets.setdefault(i, now)
                if detected:
                    self.first_detection.setdefault(i, end - self.fault_onsets[i])
            if actual and state.status == "isolated":
                self.ever_quarantined.add(i)
            if (
                step >= self.config.fault_end
                and i in self.ever_quarantined
                and state.status == "healthy"
            ):
                self.first_recovery.setdefault(i, end - self.config.fault_end * dt)
            if (
                self.config.scenario == "environment"
                and self.config.fault_start <= step < self.config.fault_end
            ):
                if v.temperature > 35:
                    self.metrics["event_node_steps"] += 1
                    self.metrics["event_false_isolations"] += int(
                        state.sensing_status == "isolated"
                    )
            self.metrics["generated"] += 1
            self.metrics["total_node_steps"] += 1
            path = route_table[i]
            self.metrics["available_node_steps"] += int(bool(path))
            old = self.routes.get(i)
            if old is not None and old != path:
                self.metrics["route_changes"] += 1
                self.metrics["control_packets"] += len(self.topology.links[i])
                self.timeline.append(
                    {
                        "time": end,
                        "node_id": i,
                        "kind": "route",
                        "message": f'Route {old} → {path or "unreachable"}',
                    }
                )
            self.routes[i] = path
            admit = (
                self.config.method == "conventional"
                or state.sensing_status == "healthy"
            )
            if not path or not admit:
                continue
            clock = end
            succeeded = True
            for a, b in zip(path, path[1:]):
                hop_ok = False
                for attempt in range(2):
                    self.metrics["data_attempts"] += 1
                    ok, latency = self.world.transmission(step, i, a, b, attempt, truth)
                    link = (min(a, b), max(a, b))
                    clock = max(clock, self.busy_until.get(link, 0))
                    self.busy_until[link] = (
                        clock + 0.005
                    )  # Explicit half-duplex link service time.
                    clock += latency / 1000
                    if ok:
                        hop_ok = True
                        break
                if not hop_ok:
                    succeeded = False
                    break
            if succeeded:
                self.serial += 1
                heapq.heappush(
                    self.packets,
                    (
                        clock,
                        self.serial,
                        i,
                        abs(v.reported_temperature - v.temperature) <= 2.0,
                        clock - end,
                    ),
                )
        # Deliver only packets whose arrival time has actually been reached.
        while self.packets and self.packets[0][0] <= end:
            _, _, node, correct, latency = heapq.heappop(self.packets)
            self.metrics["delivered"] += 1
            current = self.engine.states[node]
            if (
                self.config.method == "conventional"
                or current.sensing_status == "healthy"
            ):
                self.metrics["accepted"] += 1
                self.metrics["correct"] += int(correct)
            self.delivery_latency.append(latency)
        self.step_index += 1
        self.timeline = self.timeline[-300:]
        self.history.append(
            {
                "time": end,
                "sensing": {
                    i: round(s.sensing.score, 4) for i, s in self.engine.states.items()
                },
                "communication": {
                    i: round(s.communication.score, 4)
                    for i, s in self.engine.states.items()
                },
            }
        )
        self.history = self.history[-300:]
        self.compute_seconds += time.perf_counter() - start_clock
        return self.snapshot()

    def summary(self):
        m = self.metrics
        ratio = lambda a, b: a / b if b else None
        return {
            **m,
            "pdr": ratio(m["delivered"], m["generated"]),
            "data_reliability": ratio(m["correct"], m["accepted"]),
            "reliable_yield": ratio(m["correct"], m["generated"]),
            "availability": ratio(m["available_node_steps"], m["total_node_steps"]),
            "accuracy": ratio(m["tp"] + m["tn"], m["tp"] + m["tn"] + m["fp"] + m["fn"]),
            "fpr": ratio(m["fp"], m["fp"] + m["tn"]),
            "fnr": ratio(m["fn"], m["fn"] + m["tp"]),
            "detection_latency_s": (
                sum(self.first_detection.values()) / len(self.first_detection)
                if self.first_detection
                else None
            ),
            "recovery_time_s": (
                sum(self.first_recovery.values()) / len(self.first_recovery)
                if self.first_recovery
                else None
            ),
            "undetected_nodes": len(self.ever_faulty - set(self.first_detection)),
            "unrecovered_nodes": len(self.ever_quarantined - set(self.first_recovery)),
            "quarantined_faulty_nodes": len(self.ever_quarantined),
            "mean_delivery_latency_s": (
                sum(self.delivery_latency) / len(self.delivery_latency)
                if self.delivery_latency
                else None
            ),
            "in_flight_at_end": len(self.packets),
            "compute_seconds": self.compute_seconds,
            "control_per_generated": ratio(m["control_packets"], m["generated"]),
            "modeled_radio_energy_mj": 0.12
            * (m["data_attempts"] + m["control_packets"]),
        }

    def snapshot(self):
        return {
            "config": asdict(self.config),
            "step": self.step_index,
            "complete": self.step_index >= self.config.steps,
            "nodes": [
                {
                    "id": i,
                    "name": f"N{i:02}",
                    "x": self.topology.positions[i][0],
                    "y": self.topology.positions[i][1],
                    "sensing_trust": round(s.sensing.score, 4),
                    "communication_trust": round(s.communication.score, 4),
                    "status": s.status,
                    "sensing_status": s.sensing_status,
                    "communication_status": s.communication_status,
                    "temperature": s.temperature,
                    "humidity": s.humidity,
                    "event": s.event,
                    "reason": s.reason,
                    "route": self.routes.get(i, []),
                }
                for i, s in self.engine.states.items()
            ],
            "gateway": {
                "id": 0,
                "x": self.topology.positions[0][0],
                "y": self.topology.positions[0][1],
            },
            "links": [
                [a, b]
                for a, edges in self.topology.links.items()
                for b in edges
                if a < b
            ],
            "metrics": self.summary(),
            "history": self.history,
            "events": self.timeline,
        }

    def run(self):
        while self.step_index < self.config.steps:
            self.step()
        return self.summary()
