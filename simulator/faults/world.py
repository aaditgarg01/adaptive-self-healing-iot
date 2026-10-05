"""Evaluator-owned environment and truth. Never pass this object to TrustEngine."""

import hashlib
import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Truth:
    temperature: float
    humidity: float
    reported_temperature: float
    fault: str
    sensing_fault: bool
    communication_fault: bool


class World:
    def __init__(self, config, topology):
        self.config, self.topology = config, topology

    def uniform(self, *key):
        raw = hashlib.blake2b(
            repr((self.config.seed, *key)).encode(), digest_size=8
        ).digest()
        return int.from_bytes(raw, "big") / 2**64

    def truth(self, step, node):
        x, y = self.topology.positions[node]
        temperature = 27 + 0.1 * x + 0.05 * y + 0.3 * math.sin(step / 18)
        humidity = 58 + 0.3 * math.cos(step / 20)
        active = self.config.fault_start <= step < self.config.fault_end
        scenario = self.config.scenario
        if scenario == "environment" and active and x <= 1 and y <= 1:
            temperature += 15
        targets = {max(1, self.config.nodes // 3)}
        if scenario == "multiple":
            targets |= {
                max(2, self.config.nodes // 2),
                max(3, self.config.nodes // 2 + 1),
            }
        fault = (
            scenario
            if active and node in targets and scenario not in ("normal", "environment")
            else "none"
        )
        if fault == "multiple":
            fault = "sensor_bias" if node == min(targets) else "node_failure"
        if fault == "intermittent" and (step - self.config.fault_start) // 8 % 2:
            fault = "none"
        observed = temperature + (self.uniform(step, node, "measurement") - 0.5) * 0.4
        if fault in ("sensor_bias", "intermittent"):
            observed += 15
        if fault == "noise":
            observed += (self.uniform(step, node, "noise") - 0.5) * 24
        return Truth(
            temperature,
            humidity,
            observed,
            fault,
            fault in ("sensor_bias", "noise", "intermittent"),
            fault in ("packet_loss", "high_latency", "node_failure"),
        )

    def transmission(
        self, step, source, sender, receiver, attempt, truth, diagnostic=False
    ):
        involved = [truth[n].fault for n in (sender, receiver) if n]
        failed = "node_failure" in involved
        loss = 0.7 if "packet_loss" in involved else 0.015
        success = (
            not failed
            and self.uniform(
                step,
                source,
                sender,
                receiver,
                attempt,
                "probe" if diagnostic else "data",
            )
            >= loss
        )
        latency = (
            6000.0
            if "high_latency" in involved
            else 15
            + 25 * self.uniform(step, source, sender, receiver, attempt, "latency")
        )
        return success, latency
