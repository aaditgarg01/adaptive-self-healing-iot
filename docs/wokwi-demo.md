# Stages 2–4: local nodes, gateway and controlled faults

## Build profiles

The original `esp32dev` profile remains the Stage 1 serial-only node. The node2
and node3 profiles use identical code with stable IDs N02/N03. `demo`, `demo2` and
`demo3` enable MQTT plus fault commands and button cycling. All six node profiles
and the ESP32 gateway compiled successfully on the development machine.

```sh
pio run -d wokwi/node
pio run -d wokwi/gateway
python -m scripts.prepare_wokwi --env demo --output work/wokwi/N01
python -m scripts.prepare_wokwi --env demo2 --output work/wokwi/N02
python -m scripts.prepare_wokwi --env demo3 --output work/wokwi/N03
python -m scripts.prepare_wokwi --kind gateway --output work/wokwi/gateway
```

Open each generated folder in a **separate VS Code simulation instance**. It
contains the circuit and locally built firmware. The preparation tool uploads
nothing. N04/N05 can be added by duplicating the demo profile and changing the
`NODE_ID_VALUE` build flag; the supplied reproducible demonstration has three nodes
plus one gateway.

Wokwi does not support multiple microcontrollers in one circuit. Its public gateway
cannot reach localhost. A valid private/offline-capable setup is required to keep
these artifacts local; the inspected expired license cannot run this demonstration.
No workaround bypassing license requirements has been attempted.

## Local communication

Start a local Mosquitto broker (Docker is optional infrastructure):

```sh
docker compose up -d mqtt
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

In a separate terminal using the same Python environment:

```sh
python -m scripts.mqtt_bridge
```

Use the dashboard's **Live gateway** page or `/api/nodes` to register:

| Node | x | y |
| --- | --- | --- |
| N01 | 0 | 0 |
| N02 | 1 | 0 |
| N03 | 0 | 1 |

The broker binds to `127.0.0.1:1883` and allows anonymous clients **on the local
machine only**. It is a demonstration broker, not a production security setup.
ESP32 nodes connect via `host.wokwi.internal:1883` using `Wokwi-GUEST` channel 6.
Enable the licensed local Wokwi network bridge. Nodes publish to `iot/raw`; the
ESP32 gateway forwards unchanged JSON to `iot/telemetry`; the Python adapter posts
it to FastAPI. Broker loss does not stop serial output; MQTT retries occur every
five seconds with a bounded socket timeout. MQTT QoS 0 messages are not buffered
for guaranteed delivery. Credentials are not hardcoded.

## Fault controls

In demo profiles, enter one command followed by Enter in each node's serial monitor:

| Command | Effect |
| --- | --- |
| `NONE` | Restore normal output |
| `BIAS` | Add 15°C to reported temperature |
| `NOISE` | Deterministic pseudorandom ±12°C measurement noise |
| `LOSS` | Drop approximately 70% of transmissions |
| `LATENCY` | Queue transmissions for six seconds, bounded to eight pending messages |
| `FAILURE` | Suppress new telemetry while leaving the control loop responsive |
| `INTERMITTENT` | Alternate normal and +15°C bias in ten-second blocks |

The button cycles through these seven modes in demo profiles. In Stage 1 it remains
an LED self-test. Fault-mode labels are never put into sensor telemetry. `NONE`
stops new faults; previously queued latency messages may still arrive. MQTT connect
operations can briefly delay sampling, unlike the baseline serial-only profile.

For a genuine environmental event, change all three nearby DHT22 sensors coherently
using Wokwi's sensor controls. Temperature and humidity changes affect subsequent
readings. The full nine-scenario quantitative study is in the Python simulator;
Wokwi is a feasibility demonstration, not a radio experiment.

## Expected behavior and acceptance

- All three stable node IDs appear independently in serial/MQTT output.
- Gateway serial output mirrors forwarded JSON and its LED blinks on receipt.
- The API rejects invalid/duplicate telemetry and stores accepted packets.
- One biased node loses sensing trust while its communication remains usable.
- Two credible nearby witnesses support a coherent change.
- Switching back to `NONE` allows observed evidence to accumulate for recovery.

Changing/queued timestamps are uptime, not synchronized UTC. The live observer
measures message freshness rather than true one-way latency; it cannot reliably
identify a constant delayed stream without synchronized clocks or a round-trip
probe protocol. Wokwi network routes are broker-mediated; multi-hop rerouting and
relay-failure isolation are demonstrated by the Python simulator.

**Build checks passed; these live interactions and broker/gateway integration have
not been observed in Wokwi.** They remain acceptance work for a valid local license.
For an entirely local backend-only demonstration, replay an existing serial log:

```sh
python -m scripts.replay_serial path/to/captured.jsonl
```

This is replay, not proof of a live ESP32/Wokwi execution. Troubleshoot with the
node serial monitor first, then broker connection, gateway subscription and API
validation. Stop the optional broker with `docker compose down`.
