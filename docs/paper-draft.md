# Adaptive Trust-Aware Admission and Routing in Simulated IoT Sensor Networks

Private working manuscript. Authors, affiliations and venue are intentionally
unspecified. Not submitted or publication-ready pending the limitations below.

## Abstract

Reliable sensor-network operation requires distinguishing faulty observations,
communication failures and coherent environmental changes. We implement a
simulation-first prototype that maintains separate sensing and communication
evidence, validates readings against fresh neighboring witnesses, adapts relay
selection and monitors isolated nodes before re-admission. A deterministic network
model evaluates nine scenarios at 20, 50 and 100 nodes, using conventional and
static-threshold baselines and 30 paired seeds per configuration (2,430 runs).
The prototype preserves the tested environmental event and improves delivery over
conventional routing under relay failure. It also exhibits materially higher
false-positive state occupancy and slower recovery than the static baseline in
several scenarios. The study therefore characterizes a candidate joint control
policy and its tradeoffs, without asserting algorithmic novelty, patentability
or superiority beyond the stated model.

## 1. Problem and related work

Neighbor confidence, event/fault separation, trust-aware routing and trust recovery
are established topics. The references and preliminary comparison matrix in
`research-gap.md` must be expanded with full-text review and citation chaining.
The research question is whether separate sensing/relay decisions, coherent-context
preservation and evidence-based re-admission can jointly improve useful data
availability under mixed disturbances at acceptable control cost.

## 2. System and method

The hardware demonstrator consists of ESP32/DHT22 firmware with serial JSON and
optional broker-mediated MQTT communication. The firmware compiles, but its Wokwi
runtime has not been validated. The research evaluator is a separate software
network model with timed packet arrivals, per-hop retries, a geometric topology
and an explicitly costed diagnostic channel.

The complete reproducible formulation appears in `methodology.md`: discounted
positive/negative evidence, robust neighbor residuals, freshness gating, coherent
witness support, distinct admission/relay states, route cost and recovery
hysteresis. This specification, rather than an informal weighted sum, defines the
implemented method. The algorithm receives only observable records and declared
spatial topology; evaluator-owned truth is inaccessible to its decision interface.

## 3. Experimental design

Use the frozen `configs/benchmark.json` configuration and the exact metric
definitions in `experiments.md`. Compare conventional geometric routing, immediate
static exclusion and the adaptive policy under shared keyed disturbances. Report
run-level mean/SD/95% intervals, paired effects and corrected signed-rank tests.
Record censored detections/recoveries and distinguish admitted-data quality from
reliable yield. No model parameters were tuned against the final seeds 101–130.

## 4. Results

`results.md` is an automatically generated results chapter with the full 20-node
table and figures for all sizes. In the 20-node complete-failure scenario, mean PDR
is 78.69% for conventional routing, 96.85% for static exclusion and 97.19% for the
adaptive method. The adaptive-minus-conventional paired difference is approximately
18.505 percentage points, with a 95% interval [18.465,18.544]. In the environmental
event scenario, adaptive reliable yield exceeds static yield by about 6.413
percentage points, interval [6.386,6.441].

Contrary evidence is central: in sensor bias, adaptive reliable yield is about
1.031 percentage points below static yield, interval [−1.061,−1.000]. During normal
operation, adaptive nonhealthy-state occupancy is about 7.57%, versus 1.50% for the
static method. These results discourage a blanket claim of better fault detection
or lower false-positive rates.

## 5. Threats to validity

The gateway/controller and management channel are favorable assumptions. There is
no validated radio interference or battery model, no real environmental trace,
no hardware timing evidence and no malicious-node/collusion evaluation. Grid
geometry and a single fault location per size constrain generalization. Correlated
faults may mimic events. Humidity does not contribute to context classification.
Recovery statistics are conditional and can conceal right censoring unless counts
are shown. Computation timing is affected by host load. Baselines are transparent
reference implementations, not full reproductions of SecTrust-RPL or other papers.

## 6. Next research work

Priorities are diagnostic-channel failure, topology/fault-location sweeps,
correlated-fault stress tests, context/recovery ablations, threshold calibration on
separate data, latency/service-availability metrics and real or validated sensor
traces. Improve excessive suspicion/recovery delay before positioning the method
as an operational fault detector. Complete the Wokwi demonstration and a deeper
prior-art review before external submission or disclosure.

## References

Use the primary links in `research-gap.md` as the initial bibliography. Verify
publication metadata, full text and the target venue's format before submission.
No indexing, acceptance, novelty or IP filing outcome is claimed.
