# Local API reference

Run the backend on `127.0.0.1:8000`. Interactive OpenAPI documentation is at `/docs`
and the machine-readable schema at `/openapi.json`. The service has no multi-user
authentication and is intended only for this loopback-bound research demonstration.

| Method / path | Behavior |
| --- | --- |
| GET `/api/health` | Liveness and scope |
| GET `/api/state` | Simulation config, nodes, trust/status, topology, routes, metrics, history, events |
| POST `/api/simulation` | Reset with nodes, steps, seed, scenario and method; starts paused |
| POST `/api/play`, `/api/pause` | Start/stop accelerated interactive execution |
| POST `/api/step` | Advance one two-second simulated interval |
| POST `/api/faults` | Operator override for one virtual node; `none` restores it |
| GET `/api/experiments` | Committed validated aggregate results |
| GET `/api/runs` | Most recent 100 completed interactive runs stored in SQLite |
| POST `/api/nodes` | Register/update a live node's declared position |
| POST `/api/telemetry` | Validate and persist live telemetry; reject duplicate/stale updates |
| GET `/api/live` | Live trust state, observed data and transitions |

Examples:

```sh
curl -X POST http://127.0.0.1:8000/api/simulation -H 'Content-Type: application/json' \
  -d '{"nodes":20,"steps":240,"seed":1,"scenario":"node_failure","method":"adaptive"}'
curl -X POST http://127.0.0.1:8000/api/step
curl -X POST http://127.0.0.1:8000/api/faults -H 'Content-Type: application/json' \
  -d '{"node_id":6,"mode":"sensor_bias"}'
curl -X POST http://127.0.0.1:8000/api/nodes -H 'Content-Type: application/json' \
  -d '{"node_id":"N01","x":0,"y":0}'
```

Live telemetry has the Stage 1 JSON contract: `node_id`, `boot_id`, `sequence`,
`uptime_ms`, `temperature`, `humidity`, `timestamp`, `sensor_ok`. Unknown fields
(including fault labels) are rejected. Register a node before ingestion. Duplicate
sequence IDs return `accepted:false`; invalid payloads return HTTP 422. A supplied
timestamp must be an ISO datetime with timezone. `null` is the correct Stage 1
value without clock synchronization.

Default database: `work/iot.sqlite3`. Set `IOT_DATABASE` to choose another local
path. Registrations, telemetry and completed run summaries persist. Trust state,
current simulation and boot-session retirement metadata are currently in-memory.
Run the backend with a single worker to maintain a single consistent interactive
simulation. No WebSocket/cloud streaming or automated external actions are used.
