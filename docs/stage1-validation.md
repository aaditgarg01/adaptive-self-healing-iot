# Stage 1 validation report (historical)

This records the original Stage 1 checkpoint. The user subsequently authorized all
remaining stages; see `validation.md` for the current implementation status.

Validation date: 2026-10-05. Scope: single-node firmware only.

## Outcome

**Implementation and local tests passed. Full Stage 1 acceptance remains pending
the live Wokwi simulation. Stage 2 has not started.**

## Created files

- `wokwi/node/src/main.cpp`: DHT22 sampling, JSON, button and LED logic.
- `wokwi/node/diagram.json`: ESP32/DHT22/LED/button wiring.
- `wokwi/node/wokwi.toml`: firmware and ELF paths.
- `wokwi/node/platformio.ini`: pinned target and library build configuration.
- `wokwi/README.md`: full architecture, setup, wiring, execution and acceptance guide.
- `README.md`: project scope, privacy constraints and research status.
- `.gitignore`: excludes build products, local environments and credentials.
- `tests/stage1/test_stage1.py`, `firmware_harness.cpp` and four headers under
  `tests/stage1/stubs/`: deterministic local application tests.
- `docs/stage1-validation.md`: this report.

## Target build evidence

- PlatformIO Core: 6.1.19.
- Espressif32 platform: 6.13.0; board: esp32dev.
- Arduino framework package: 3.20017.241212+sha.dcc1105b.
- Xtensa compiler package: 8.4.0+2021r2-patch5.
- DHT sensor library for ESPx: 1.19.0.
- Result: SUCCESS; `firmware.bin` and `firmware.elf` generated.
- Reported RAM: 21,616 / 327,680 bytes (6.6%).
- Reported application flash: 271,349 / 1,310,720 bytes (20.7%).

These are compiler/linker size estimates, not measured runtime memory peaks or
energy consumption. No physical board or Wokwi execution is implied.

The build used a workspace-local PlatformIO core/cache with links to already
installed target packages. From the checkout, the command used was:

```sh
PLATFORMIO_CORE_DIR=/Users/aaditgarg/Documents/Codex/2026-10-05/use/work/platformio \
  /Users/aaditgarg/.platformio/penv/bin/pio run -d wokwi/node
```

For a normal installation, `pio run -d wokwi/node` is sufficient.

## Tests actually performed

`python3 tests/stage1/test_stage1.py` compiled the real firmware source with
clang++ using `-Wall -Wextra -Werror`, then executed the harness and parsed 14 JSON
telemetry lines. All five test groups passed:

1. Required JSON fields, strict numeric validity, sequence continuity and stable
   boot identifier within a session.
2. Two-second schedule, no catch-up bursts, and uptime beyond 32-bit rollover.
3. Changed sensor inputs (27°C/58% → 35.5°C/72%) and button presses preserving data.
4. NaN, infinity, out-of-range humidity, timeout and checksum errors, followed by
   valid readings; associated green/red GPIO states.
5. Diagram structure, expected wire endpoints and build-path configuration.

The C++ harness also asserts serial baud, GPIO configuration, 40 ms debounce,
500 ms LED indication and no retrigger on a held button. Diagram assertions are
structural checks, not a full Wokwi electrical/part validator.

## Live simulation limitation

Wokwi extensions 3.6.0 and 3.7.0 are installed. Inspection of local configuration
found an expired license (2026-03-29), no offline entitlement and no cached engine.
No license was modified and no paid service was purchased. The firmware was not
submitted to the Wokwi website or cloud CI.

Consequently no live sensor-slider change, LED rendering, button interaction,
reset or sensor-disconnection test has been observed in Wokwi. The complete manual
procedure is in `wokwi/README.md`. Full acceptance cannot be claimed yet.

## Privacy and research boundaries

An authenticated, read-only GitHub API check returned `private: true` and
`visibility: private` for `aaditgarg01/adaptive-self-healing-iot`. No push, public
project, external technical publication or algorithm implementation was made.

Only public dependency downloads and documentation lookups were performed.
Candidate trust/context/reintegration mechanisms remain unproven research ideas.
There are no research experiments or numerical research claims in Stage 1.
Test fixture values are confined to tests and are not inputs to a trust algorithm.

## Remaining acceptance work

Provision a valid offline-capable Wokwi setup, run the supplied circuit, collect
local serial output, confirm DHT22 slider changes and LED/button behavior, and
complete the live checks in the guide. Record the outcome before considering
Stage 1 accepted. Explicit approval is still required before Stage 2.
