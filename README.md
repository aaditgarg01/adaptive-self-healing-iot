# Adaptive Trust-Aware Self-Healing IoT Sensor Network

A private, simulation-first research prototype for **adaptive trust → contextual
validation → fault detection → route adaptation → monitored recovery**.

The software demonstration is implemented and tested: 20–100 nodes, all nine
requested scenarios, two trust dimensions, neighborhood validation, routing,
a FastAPI/SQLite backend, a React dashboard and reproducible benchmarking.
The ESP32 node variants and gateway compile successfully. **Live Wokwi execution
remains unverified** because the available license is expired and lacks offline
support. See [validation status](docs/validation.md) for exact boundaries.

The proposed mechanism is a **candidate research contribution**, not an established
novel invention. No patentability or publication guarantee is claimed.

## Run the local dashboard

Requires Python 3.11+ and Node.js 22.12+ (tested with Python 3.13 and Node 26).
From the repository root:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
npm ci --prefix frontend
npm run build --prefix frontend
.venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Open **http://127.0.0.1:8000**. The server binds only to loopback. Choose a scenario,
node count, method and seed, press **Reset experiment**, then **Run**. Select a node
to inspect both trust scores, its route and the timeline. Use the **Experiments**
view for the included measured benchmark summaries. The **Live gateway** view is
separate from the simulator and accepts locally ingested sensor telemetry.

For development, run the backend and `npm run dev --prefix frontend` in separate
terminals. Vite proxies `/api` to the local backend.

## Run without a dashboard

```sh
.venv/bin/python -m scripts.run_demo --scenario node_failure --nodes 20 --seed 1
.venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v
.venv/bin/python tests/stage1/test_stage1.py
```

The firmware application tests need clang++ or g++. API/simulator tests require no
physical hardware, broker, cloud account or Wokwi subscription.

## Reproduce the experiments

```sh
.venv/bin/python -m simulator.experiments.run --config configs/benchmark.json --output results/reproduced
```

The included `results/validated/` contains **2,430 actual runs**: 30 paired seeds ×
9 scenarios × 3 methods × 3 sizes (20/50/100). It includes per-run JSONL/CSV, means,
standard deviations, 95% intervals, paired statistical comparisons and figures.
See [experiment protocol](docs/experiments.md) and [measured results](docs/results.md).

The adaptive method is **not uniformly better**. It preserves the tested coherent
environmental event and avoids failed relays, but its conservative trust recovery
increases false-positive state occupancy and reduces yield in some sensor-fault
scenarios. Those limitations are retained in the results rather than hidden.

## ESP32 and Wokwi

```sh
python3 -m pip install platformio==6.1.19
pio run -d wokwi/node
pio run -d wokwi/gateway
```

See [Stage 1 wiring and telemetry](wokwi/README.md) and
[multi-node/gateway/fault demonstration](docs/wokwi-demo.md). Do not upload this
project to the Wokwi website or cloud CI under the current privacy instruction.
Use a licensed offline-capable local simulator. MQTT demonstration additionally
requires a local broker and Wokwi network bridge.

## Repository map

| Directory | Purpose |
| --- | --- |
| `wokwi/node`, `wokwi/gateway` | ESP32 firmware, build profiles and circuits |
| `simulator/models.py` | Observable records, trust evidence and run settings |
| `simulator/faults` | Evaluator-owned environmental truth and fault schedules |
| `simulator/trust` | Observation-only trust/context controller |
| `simulator/network`, `simulator/routing` | Topology and weighted shortest paths |
| `simulator/simulation.py` | Timed packet/probe execution and evaluation |
| `simulator/experiments` | Repetitions, summaries, statistical tests and charts |
| `backend` | REST APIs, live observer and SQLite persistence |
| `frontend` | React/TypeScript/Vite dashboard using local system fonts |
| `scripts`, `infra`, `compose.yaml` | Local demos, telemetry adapters and optional broker |
| `results/validated` | Final measured benchmark artifacts |
| `tests` | Firmware application, simulator, routing and API tests |
| `docs` | Architecture, methodology, results, prior art and validation |

## Research and privacy boundaries

Keep the repository private. No public site, public Wokwi project, paper upload or
cloud CI is configured. Pushing this work to the user's specified private GitHub
repository is authorized; making it public is not.

Fault labels and true environmental values exist only in the simulator/evaluator.
The trust engine receives telemetry, delivery/latency observations and declared
spatial topology. It never receives fault labels. The software uses an explicitly
costed, separate diagnostic channel; it is not a validated physical-radio model.

The implementation uses a small standard-library event scheduler and shortest-path
router instead of adding SimPy/NetworkX, and plain CSS instead of Tailwind. These
choices keep dependencies small without changing the approved two-layer design.

Further reading: [architecture](docs/architecture.md), [methodology](docs/methodology.md),
[API](docs/api.md), [stage roadmap and commands](docs/stages.md),
[research gap](docs/research-gap.md), [IP notes](docs/patent-notes.md),
[paper draft](docs/paper-draft.md).
