from contextlib import asynccontextmanager
from dataclasses import asdict
import asyncio
import math
import os
from pathlib import Path
import threading
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from simulator.models import Config, SCENARIOS, METHODS
from simulator.simulation import Simulation
from backend.storage import Store
from backend.live import LiveObserver

ROOT = Path(__file__).resolve().parents[1]


class StartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nodes: int = Field(20, ge=3, le=100)
    steps: int = Field(180, ge=30, le=2000)
    seed: int = Field(1, ge=0, le=2**31 - 1)
    scenario: str = "sensor_bias"
    method: str = "adaptive"

    @field_validator("scenario")
    @classmethod
    def scenario_valid(cls, v):
        if v not in SCENARIOS:
            raise ValueError("unknown scenario")
        return v

    @field_validator("method")
    @classmethod
    def method_valid(cls, v):
        if v not in METHODS:
            raise ValueError("unknown method")
        return v


class FaultRequest(BaseModel):
    node_id: int
    mode: str


class RegisterRequest(BaseModel):
    node_id: str = Field(pattern=r"^N(?:0[1-9]|[1-9][0-9]|100)$")
    x: float = Field(ge=-1000, le=1000, allow_inf_nan=False)
    y: float = Field(ge=-1000, le=1000, allow_inf_nan=False)


class Telemetry(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    node_id: str = Field(pattern=r"^N(?:0[1-9]|[1-9][0-9]|100)$")
    boot_id: str = Field(pattern=r"^[0-9a-f]{32}$")
    sequence: int = Field(ge=1, le=2**63 - 1)
    uptime_ms: int = Field(ge=0, le=2**63 - 1)
    temperature: float | None = Field(default=None, ge=-40, le=80)
    humidity: float | None = Field(default=None, ge=0, le=100)
    timestamp: str | None = None
    sensor_ok: bool

    @model_validator(mode="after")
    def consistent(self):
        if self.sensor_ok and (self.temperature is None or self.humidity is None):
            raise ValueError("valid reading requires both values")
        if not self.sensor_ok and (
            self.temperature is not None or self.humidity is not None
        ):
            raise ValueError("invalid reading requires null values")
        if self.timestamp is not None:
            from datetime import datetime

            parsed = datetime.fromisoformat(self.timestamp.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                raise ValueError("timestamp must include timezone")
        return self


class Runtime:
    def __init__(self, db):
        self.store = Store(db)
        self.live = LiveObserver(self.store)
        self.sim = Simulation()
        self.playing = False
        self.saved = False
        self.lock = threading.RLock()

    def advance(self):
        self.sim.step()
        if self.sim.step_index >= self.sim.config.steps:
            self.playing = False
            if not self.saved:
                self.store.save_run(asdict(self.sim.config), self.sim.summary())
                self.saved = True


def create_app(db_path=None):
    @asynccontextmanager
    async def lifespan(app):
        runtime = Runtime(
            db_path or os.environ.get("IOT_DATABASE", str(ROOT / "work/iot.sqlite3"))
        )
        app.state.runtime = runtime

        async def ticker():
            while True:
                await asyncio.sleep(0.25)
                with runtime.lock:
                    runtime.live.tick()
                    if runtime.playing:
                        runtime.advance()

        task = asyncio.create_task(ticker())
        yield
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        runtime.store.close()

    app = FastAPI(title="Adaptive IoT Local Lab", version="1.0.0", lifespan=lifespan)

    def rt():
        return app.state.runtime

    @app.get("/api/health")
    def health():
        return {"status": "ok", "scope": "local simulation research prototype"}

    @app.get("/api/state")
    def state():
        with rt().lock:
            return {**rt().sim.snapshot(), "playing": rt().playing}

    @app.post("/api/simulation")
    def start(request: StartRequest):
        with rt().lock:
            values = request.model_dump()
            steps = values["steps"]
            rt().sim = Simulation(
                Config(**values, fault_start=steps // 4, fault_end=steps * 2 // 3)
            )
            rt().saved = False
            rt().playing = False
            return rt().sim.snapshot()

    @app.post("/api/play")
    def play():
        with rt().lock:
            rt().playing = True
        return {"playing": True}

    @app.post("/api/pause")
    def pause():
        with rt().lock:
            rt().playing = False
        return {"playing": False}

    @app.post("/api/step")
    def step():
        with rt().lock:
            rt().advance()
            return rt().sim.snapshot()

    @app.post("/api/faults")
    def fault(request: FaultRequest):
        with rt().lock:
            try:
                rt().sim.inject(request.node_id, request.mode)
            except ValueError as e:
                raise HTTPException(422, str(e))
        return {"ok": True}

    @app.get("/api/experiments")
    def experiments():
        path = ROOT / "results/validated/processed/summary.json"
        import json

        return json.loads(path.read_text()) if path.exists() else []

    @app.get("/api/runs")
    def runs():
        with rt().lock:
            return rt().store.runs()

    @app.post("/api/nodes")
    def register(request: RegisterRequest):
        with rt().lock:
            rt().live.register(request.node_id, request.x, request.y)
        return {"registered": request.node_id}

    @app.post("/api/telemetry")
    def telemetry(request: Telemetry):
        with rt().lock:
            try:
                accepted = rt().live.ingest(request.model_dump())
            except ValueError as e:
                raise HTTPException(422, str(e))
        return {"accepted": accepted}

    @app.get("/api/live")
    def live():
        with rt().lock:
            rt().live.tick()
            return rt().live.snapshot()

    if (ROOT / "frontend/dist").exists():
        app.mount(
            "/",
            StaticFiles(directory=ROOT / "frontend/dist", html=True),
            name="dashboard",
        )
    return app


app = create_app()
