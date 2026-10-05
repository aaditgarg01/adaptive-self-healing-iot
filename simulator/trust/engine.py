"""Trust engine accepts observations and topology only; it never imports the fault world."""

from statistics import median
from simulator.models import NodeState


class TrustEngine:
    def __init__(self, topology, method="adaptive", context=True, recovery=True):
        self.topology, self.method, self.context, self.recovery = (
            topology,
            method,
            context and method == "adaptive",
            recovery,
        )
        self.states = {i: NodeState() for i in topology.neighbors}
        self.events = []

    def transition(self, node, dimension, quality, time):
        state = self.states[node]
        score = getattr(state, dimension).score
        field = dimension + "_status"
        previous = getattr(state, field)
        counter = dimension + "_good"
        good = (
            getattr(state, counter) + 1 if quality is not None and quality >= 0.8 else 0
        )
        setattr(state, counter, good)
        if self.method == "conventional":
            current = "healthy"
        elif self.method == "static":
            current = "healthy" if quality is None or quality >= 0.5 else "isolated"
            if quality is not None:
                getattr(state, dimension).positive = max(0.001, quality)
                getattr(state, dimension).negative = max(0.001, 1 - quality)
        elif previous == "isolated":
            current = (
                "recovering"
                if self.recovery and score >= 0.75 and good >= 5
                else "isolated"
            )
            if current == "recovering":
                setattr(state, counter, 0)
        elif previous == "recovering":
            current = (
                "isolated"
                if quality is not None and quality < 0.5
                else ("healthy" if good >= 5 else "recovering")
            )
        else:
            current = (
                "isolated"
                if score < 0.4
                else ("suspicious" if score < 0.7 else "healthy")
            )
        setattr(state, field, current)
        if current != previous:
            self.events.append(
                {
                    "time": time,
                    "node_id": node,
                    "kind": current,
                    "dimension": dimension,
                    "message": f"{dimension}: {previous} → {current}",
                }
            )

    def update(self, observations, time):
        if self.method == "conventional":
            for obs in observations:
                if obs.delivered:
                    self.states[obs.node_id].temperature = obs.temperature
                    self.states[obs.node_id].humidity = obs.humidity
            return
        received = {
            o.node_id: o
            for o in observations
            if o.delivered
            and o.sensor_ok
            and o.temperature is not None
            and o.latency_ms is not None
            and o.latency_ms <= 1000
        }
        # Snapshot peer eligibility prevents node iteration order influencing evidence.
        trusted = {
            i
            for i, s in self.states.items()
            if s.sensing.score >= 0.65 and s.sensing_status != "isolated"
        }
        for obs in observations:
            state = self.states[obs.node_id]
            state.event = False
            comm = (
                0.0
                if not obs.delivered
                else max(0.0, min(1.0, 1 - (obs.latency_ms or 0) / 2000))
            )
            state.communication.update(comm, penalty=6)
            quality = None
            if obs.delivered and not obs.sensor_ok:
                quality = 0.0
                state.reason = "invalid sensor reading"
            elif obs.node_id in received:
                value = obs.temperature
                peers = [
                    received[i].temperature
                    for i in self.topology.neighbors[obs.node_id]
                    if i in received and i in trusted
                ]
                state.temperature, state.humidity = value, obs.humidity
                if len(peers) >= 2:
                    center = median(peers)
                    scale = max(
                        0.5, min(2.0, 1.4826 * median(abs(p - center) for p in peers))
                    )
                    agreement = sum(abs(value - p) <= 1.5 for p in peers)
                    jump = (
                        state.last_temperature is not None
                        and abs(value - state.last_temperature) > 3
                    )
                    coherent = self.context and agreement >= 2
                    threshold = 3.0 * scale if self.method != "static" else 2.0
                    residual = abs(value - center)
                    # A local event boundary can have a mixed neighborhood; require two close witnesses.
                    quality = (
                        1.0
                        if coherent
                        or (residual <= threshold and (self.context or not jump))
                        else 0.0
                    )
                    state.event = bool(coherent and jump)
                    state.reason = (
                        "coherent environmental change"
                        if state.event
                        else (
                            "neighbor disagreement"
                            if quality == 0
                            else "consistent readings"
                        )
                    )
                    if state.event:
                        self.events.append(
                            {
                                "time": time,
                                "node_id": obs.node_id,
                                "kind": "environment",
                                "dimension": "sensing",
                                "message": state.reason,
                            }
                        )
                else:
                    state.reason = "insufficient fresh trusted neighbors"
                state.last_temperature = value
            else:
                state.reason = "missing or late diagnostic observation"
            state.sensing.update(quality)
            self.transition(obs.node_id, "sensing", quality, time)
            self.transition(obs.node_id, "communication", comm, time)
        self.events = self.events[-1000:]
