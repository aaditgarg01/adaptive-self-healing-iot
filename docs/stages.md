# Stage-by-stage implementation and demonstration guide

The user authorized completing all stages after reviewing Stage 1. Stages 1–4
have compiled artifacts but retain an explicit Wokwi runtime acceptance blocker.
The software stages are executable without Wokwi or physical hardware.

| Stage | Implementation / files | Run and expected check |
| --- | --- | --- |
| 1: single node | `wokwi/node/src/main.cpp`, circuit/config | `pio run -d wokwi/node -e esp32dev`; see `wokwi/README.md` for JSON and slider checks |
| 2: multiple nodes | `node2`, `node3` build profiles | Build profiles, prepare separate workspaces; expect distinct N01/N02/N03 IDs |
| 3: gateway | `wokwi/gateway`, `scripts/mqtt_bridge.py`, broker config | Build gateway; use `docs/wokwi-demo.md`; expect forwarded, validated JSON |
| 4: fault controls | `wokwi/node/src/demo.h`, demo profiles | Send NONE/BIAS/NOISE/LOSS/LATENCY/FAILURE/INTERMITTENT to serial input |
| 5: trust | `simulator/models.py`, `simulator/trust/engine.py` | Run sensor-bias demo; sensing trust falls independently of communication |
| 6: context | same engine, explicit fresh-neighbor eligibility | Run environment demo; coherent group remains sensing-healthy |
| 7: healing/routing | `simulator/routing/router.py`, recovery state machine | Run node-failure demo; routes avoid isolated relay and probation is observed |
| 8: scale | `simulator/simulation.py`, topology/fault modules | Set 20/50/100 nodes; every run has deterministic exogenous disturbances |
| 9: dashboard/backend | `frontend`, `backend` | Build frontend/start backend; overview, live, experiments and methodology views |
| 10: experiments | `simulator/experiments/run.py`, config/results | Execute 2,430 paired runs; generate raw data, tables, tests and plots |
| 11: optimization | reverse Dijkstra + reference cost test | Tests establish equal path cost; measured profile identifies hash/delivery overhead |
| 12: documentation | docs directory and root README | Architecture, API, methodology, measured results, paper draft and preliminary IP notes |

## Commands for software demonstrations

From the repository root with dependencies installed:

```sh
python -m scripts.run_demo --scenario sensor_bias --nodes 20 --seed 1 --output work/bias.json
python -m scripts.run_demo --scenario environment --nodes 20 --seed 1 --output work/event.json
python -m scripts.run_demo --scenario node_failure --nodes 100 --seed 1 --output work/failure.json
python -m unittest discover -s tests -p 'test_*.py' -v
python tests/stage1/test_stage1.py
```

The CLI prints measured summary values and writes local snapshots containing trust
histories, routes and events. Exact values depend on the chosen seed/method; the
committed benchmark tables are measured outputs, not expected-output promises.
For the dashboard, the root README provides the exact build and run commands.

## Presentation sequence

1. Show normal operation and both trust dimensions.
2. Reset to sensor bias; inspect the designated node and observe measurement
   exclusion while its communication dimension remains healthy.
3. Reset to node failure; inspect alternate routes and continuing delivered data.
4. Continue past the fault interval to inspect evidence-based recovery/probation.
5. Reset to the environmental event; show coherent observations being preserved.
6. Open Experiments and compare against conventional/static methods, including
   the adaptive method's higher false-positive occupancy and slower recovery.
7. Explain the observation/truth boundary and the diagnostic-channel assumption.

## Troubleshooting

- Empty dashboard: build `frontend/dist` before starting the backend; refresh after
  server restart. Inspect `/api/health` and local server logs.
- Port 8000 in use: stop the earlier local instance or choose another loopback port.
  Vite's development proxy defaults to 8000 and must match the backend.
- No experiment table: verify `results/validated/processed/summary.json` exists.
  Benchmark outputs at another path are not automatically selected by the UI.
- Registration rejected: IDs must be N01–N99 or N100 and coordinates finite.
- Telemetry rejected: register first, use complete JSON, avoid out-of-order sequences
  within a boot, and keep fault labels out of the observation payload.
- An isolated node does not recover by run end: inspect `unrecovered_nodes`; extend
  observation time for demonstration rather than claiming a censored recovery.
- A partition has no route: expected. The software never fabricates connectivity.
- Offline Wokwi cannot start: resolve the license/engine prerequisite; a successful
  build or software test does not substitute for live Wokwi validation.
