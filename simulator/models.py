"""Observable contracts. Ground-truth types deliberately live elsewhere."""

from dataclasses import dataclass, field
from typing import Literal
import math

SCENARIOS = (
    "normal",
    "sensor_bias",
    "noise",
    "packet_loss",
    "high_latency",
    "node_failure",
    "intermittent",
    "multiple",
    "environment",
)
METHODS = ("conventional", "static", "adaptive")


@dataclass(frozen=True)
class Config:
    nodes: int = 20
    steps: int = 180
    seed: int = 1
    scenario: str = "sensor_bias"
    method: str = "adaptive"
    fault_start: int = 40
    fault_end: int = 120
    interval_s: float = 2.0
    context: bool = True
    recovery: bool = True
    communication_radius: float = 1.5
    sensing_radius: float = 1.5

    def __post_init__(self):
        if not 3 <= self.nodes <= 100:
            raise ValueError("nodes must be 3–100")
        if not 10 <= self.steps <= 10000:
            raise ValueError("steps must be 10–10000")
        if not 0 <= self.fault_start < self.fault_end <= self.steps:
            raise ValueError("invalid fault interval")
        if self.scenario not in SCENARIOS or self.method not in METHODS:
            raise ValueError("unknown scenario/method")
        if not math.isfinite(self.interval_s) or self.interval_s <= 0:
            raise ValueError("invalid sampling interval")
        if not all(
            math.isfinite(v) and v > 0
            for v in (self.communication_radius, self.sensing_radius)
        ):
            raise ValueError("invalid radius")


@dataclass(frozen=True)
class Observation:
    node_id: int
    temperature: float | None
    humidity: float | None
    delivered: bool
    latency_ms: float | None
    sensor_ok: bool = True


@dataclass
class Evidence:
    positive: float = 9.0
    negative: float = 1.0

    @property
    def score(self):
        return self.positive / (self.positive + self.negative)

    def update(self, quality, penalty=3.0):
        if quality is None:
            return
        quality = min(1.0, max(0.0, quality))
        self.positive = 1 + 0.95 * (self.positive - 1) + quality
        self.negative = 1 + 0.95 * (self.negative - 1) + penalty * (1 - quality)


@dataclass
class NodeState:
    sensing: Evidence = field(default_factory=Evidence)
    communication: Evidence = field(default_factory=Evidence)
    sensing_status: str = "healthy"
    communication_status: str = "healthy"
    sensing_good: int = 0
    communication_good: int = 0
    temperature: float | None = None
    humidity: float | None = None
    last_temperature: float | None = None
    event: bool = False
    reason: str = "warming up"

    @property
    def status(self):
        for status in ("isolated", "recovering", "suspicious"):
            if status in (self.sensing_status, self.communication_status):
                return status
        return "healthy"
