# Stage 1: single-node Wokwi prototype

This guide describes the preserved serial-only `esp32dev` profile. Later stages
are authorized and implemented separately; see [the extended demonstration](../docs/wokwi-demo.md).

## Scope and status

One ESP32 DevKit v1 reads one DHT22 and emits newline-delimited JSON at 115200 baud
every two seconds of device time. No trust algorithm, networking, multi-node
logic or measurement fault injection is implemented.

The target firmware build and local application tests passed. Live Wokwi tests
are **pending**, because this machine's installed license is expired, does not
include offline mode, and has no cached simulation engine. Do not interpret the
local hardware substitutes as a Wokwi or physical-device test.

## Architecture

`src/main.cpp` contains small, separate functions:

| Function | Responsibility |
| --- | --- |
| `setup` | Initialize serial, GPIO, DHT22 and a per-boot diagnostic ID |
| `uptimeMs` | Read the ESP32 64-bit monotonic timer in milliseconds |
| `readSensor` | Read DHT22, check driver status, finite values and physical ranges |
| `emitTelemetry` | Serialize one complete JSON line, including errors as nulls |
| `serviceButton` | Debounce button input and schedule a brief LED self-test |
| `updateStatusLeds` | Reflect reading validity or the LED self-test |
| `loop` | Service inputs and schedule sampling without a two-second blocking delay |

The first sample occurs about two seconds after initialization. Subsequent
samples are at least 2000 ms apart, plus normal scheduler jitter. A delayed loop
does not create a burst of catch-up reads. DHT22 reads are synchronous, so the
button may be delayed briefly while a sensor transaction finishes.

## Wiring

The supplied diagram contains an ESP32, DHT22, two LEDs, two 220 Ω resistors, one
10 kΩ pull-up and a pushbutton. `D15` in the diagram means GPIO 15.

| Component pin | ESP32 / connection |
| --- | --- |
| DHT22 VCC | 3V3 |
| DHT22 GND | GND |
| DHT22 SDA | GPIO 15; 10 kΩ pull-up from SDA to 3V3 |
| DHT22 NC | Unconnected |
| Green LED anode | GPIO 18 through 220 Ω resistor |
| Green LED cathode | GND |
| Red LED anode | GPIO 19 through 220 Ω resistor |
| Red LED cathode | GND |
| Button side 1 | GPIO 23, configured as `INPUT_PULLUP` |
| Button side 2 | GND |
| ESP32 TX0 / RX0 | Wokwi serial monitor RX / TX |

Initial DHT22 settings are **27°C and 58% relative humidity**.

LED behavior:

- Before the first sample: both off.
- Valid sample: green on, red off.
- Failed/invalid reading: green off, red on, until a valid reading arrives.
- Button press: both on for 500 ms, then restore the reading state.
- Debounce is 40 ms. Holding the button does not retrigger the self-test.

The button is reserved for later fault modes. Stage 1 never modifies the measured
temperature or humidity because of a button press. The red LED indicates local
read validity or its self-test, not a trust-engine decision.

## Build locally

Prerequisites: Python, PlatformIO Core, and VS Code with the Wokwi extension for
interactive simulation. The local tests require Python 3.11+ and clang++ or g++.

From the repository root, a fresh environment can be prepared with:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install platformio==6.1.19
.venv/bin/pio run -d wokwi/node
```

With PlatformIO already installed:

```sh
pio run -d wokwi/node
```

On this machine, PlatformIO is installed at
`/Users/aaditgarg/.platformio/penv/bin/pio`. The normal build command is:

```sh
/Users/aaditgarg/.platformio/penv/bin/pio run -d wokwi/node
```

`platformio.ini` pins Espressif32 6.13.0 and DHTesp 1.19.0. It sets the
`esp32dev` board, Arduino framework and 115200 monitor speed. The DHTesp package
is named `DHT sensor library for ESPx`, which Wokwi recommends for ESP32.

Build products:

```text
wokwi/node/.pio/build/esp32dev/firmware.bin
wokwi/node/.pio/build/esp32dev/firmware.elf
```

These paths match `wokwi.toml`. This program uses the standard flash layout and
does not need a custom partition table. Builds need dependency downloads the
first time, but no project-source upload.

## Run Wokwi while keeping the project private

Use a valid **offline-capable Wokwi license and installed/cached offline engine**.
Wokwi documents offline operation as a Pro feature. Provision the engine/license
without submitting this project's files to a cloud service. Offline access has
not been provisioned by this implementation.

1. Build the firmware locally as above.
2. In VS Code, open `wokwi/node` as the workspace folder.
3. With the offline engine available and the network disconnected, open the
   command palette and choose **Wokwi: Start Simulator**.
4. Confirm the tab says **Wokwi Simulator (Offline)**. If it requests a license,
   internet access or engine download, stop and resolve that setup first.
5. Wait for the first sample. The serial monitor should show JSON telemetry,
   with green on and red off.
6. Click the DHT22 and set temperature to **35.5°C** and humidity to **72%**.
7. Observe those values in the next fresh reading (allow up to two sample periods
   for UI/read timing). Restore 27°C and 58% and check they return.
8. Press the blue button. Both LEDs should illuminate for half a second while
   sampling and sensor values continue normally.

Do not paste the project into the Wokwi website, create a public project or use
cloud Wokwi CI under the current no-external-disclosure instruction. No paid
subscription has been purchased or changed.

## Telemetry contract

Each application line is a JSON object. ESP32 ROM/bootloader startup messages
can appear before the application starts; a reader should ignore non-JSON lines.

| Field | Meaning |
| --- | --- |
| `node_id` | Stable configured node name, `N01` |
| `boot_id` | 32 hexadecimal characters generated at startup; constant within a boot |
| `sequence` | Integer starting at 1; increments for every sampling attempt |
| `uptime_ms` | Monotonic milliseconds since boot, captured before the sensor read |
| `temperature` | Celsius, two decimal places; null on invalid reading |
| `humidity` | Relative humidity percent, two decimal places; null on invalid reading |
| `timestamp` | Null: UTC is unavailable without RTC or time synchronization |
| `sensor_ok` | Boolean from driver status, finite-value and range checks |

`timestamp` is deliberately not fabricated from uptime. A future synchronized
timestamp can use UTC without changing `uptime_ms`. Temperature validity spans
−40 to 80°C; humidity spans 0 to 100%. If either value or the driver status is
invalid, both values are null. NaN/Infinity are never emitted as JSON numbers.

`boot_id` is a diagnostic identifier, not an authenticated identity or guaranteed
globally unique key. Simulated RNG state can repeat across fresh simulator runs;
future experiment files must additionally carry an evaluator-owned run ID.

Illustrative output only (not captured from a Wokwi run):

```json
{"node_id":"N01","boot_id":"b243890ca716e05587c180e113d5bb64","sequence":1,"uptime_ms":2000,"temperature":27.00,"humidity":58.00,"timestamp":null,"sensor_ok":true}
{"node_id":"N01","boot_id":"b243890ca716e05587c180e113d5bb64","sequence":2,"uptime_ms":4000,"temperature":35.50,"humidity":72.00,"timestamp":null,"sensor_ok":true}
```

Illustrative sensor read error:

```json
{"node_id":"N01","boot_id":"b243890ca716e05587c180e113d5bb64","sequence":3,"uptime_ms":6000,"temperature":null,"humidity":null,"timestamp":null,"sensor_ok":false}
```

## Repeat local application tests

From the repository root:

```sh
python3 tests/stage1/test_stage1.py
```

The harness compiles the actual `main.cpp` against deterministic test-only
substitutes for GPIO, serial, clock, RNG and the DHT driver. Python then strictly
parses and checks the resulting JSON. It checks the two-second schedule, a sensor
value change, button bounce/hold behavior, invalid readings, restored readings,
long uptime and expected circuit connections. No substitute is included in the
ESP32 build. These tests do not verify electrical timing or Wokwi rendering.

## Stage 1 acceptance checklist

| Criterion | Current evidence |
| --- | --- |
| Target firmware compiles and fits ESP32 | Passed target build |
| Required fields and valid JSON | Passed local application tests |
| Two-second device-time sampling | Passed deterministic scheduler tests; live check pending |
| 115200 baud configured | Passed application test and build configuration check |
| DHT22 readings change with inputs | Passed driver-substitute test; Wokwi slider check pending |
| Green/red LED behavior | Passed GPIO-substitute test; visual check pending |
| Debounced button without data corruption | Passed application tests; visual check pending |
| Missing sensor yields nulls and red LED | Passed driver-error tests; live check pending |
| Clean reset: sequence restarts; boot ID stable within run | Sequence/stability tested; live reset pending |
| Complete live single-node Wokwi demonstration | Pending valid offline setup |

For live error checking, stop the simulator, temporarily disconnect DHT SDA,
restart and verify null readings and red LED. Restore the wire and restart.
Run normal mode for at least 60 simulated seconds, parse all application lines,
check sequence continuity and inspect successive `uptime_ms` differences. Record
the trace and screenshots locally before marking the live checks passed.

**Stage 1 runtime acceptance remains pending the Wokwi checks. The user subsequently
approved all remaining stages; see the current validation report for their status.**

## Troubleshooting and limits

- **License expired/offline unavailable:** renew/provision an appropriate Wokwi
  setup. This environment's inspected license expired on 2026-03-29 and does not
  enable offline mode. There is no cached engine in either installed extension.
- **Firmware not found:** build first; open `wokwi/node`, or use **Wokwi: Select
  Config File** to select its `wokwi.toml`.
- **Only boot messages:** wait at least two simulated seconds. Keep the simulator
  visible; device time may advance slower than wall-clock time.
- **Null readings/red LED:** check DHT SDA/GPIO15, 3V3, common ground, pull-up and
  the pinned DHTesp library. Do not lower the sampling interval below two seconds.
- **Button appears inactive:** wait for the debounce period; its only Stage 1
  effect is a 500 ms LED self-test. Opposite button contacts must connect GPIO23
  and ground.
- **Timestamp is null:** expected without RTC/NTP; uptime and sequence remain
  available for relative ordering.
- **Multiple boards:** Wokwi does not currently support multiple microcontrollers
  in one project. This does not affect the single-board Stage 1 circuit.

References: [project configuration](https://docs.wokwi.com/vscode/project-config),
[DHT22](https://docs.wokwi.com/parts/wokwi-dht22),
[offline mode](https://docs.wokwi.com/vscode/offline-mode),
[Wokwi FAQ](https://docs.wokwi.com/faq).
