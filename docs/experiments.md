# Reproducible experiment protocol

## Final benchmark

Run `python -m simulator.experiments.run --config configs/benchmark.json --output
results/reproduced` from the repository root. The committed final artifacts are
in `results/validated/`; development/pilot outputs are excluded from version control.

- Sizes: 20, 50, 100 nodes; geometric grid topology.
- Scenarios: normal, bias, noise, packet loss, latency, complete failure,
  intermittent bias, multiple faults, genuine environmental event.
- Methods: conventional, static and adaptive.
- Repetitions: 30 paired seeds (101–130) for every size/scenario/method.
- Duration: 240 steps × 2 seconds = 480 simulated seconds.
- Fault/event window: steps 40–139 inclusive, followed by 100 recovery steps.
- Total: 2,430 independently executed simulations.

Development runs used earlier seeds. They exposed overly slow recovery and a
misleading recovery statistic for methods that never quarantined nodes. Evidence
discounting and the recovery denominator were corrected before the final seed
range was run. No parameter was tuned after examining the final benchmark.
This is internal synthetic validation, not an independent real-world dataset.

## Metrics and denominators

| Metric | Definition |
| --- | --- |
| Accuracy | Correct fault-state classification / all evaluated node-steps |
| FPR | Healthy labeled node-steps reported suspicious/isolated/recovering / healthy node-steps |
| FNR | Faulty labeled node-steps reported healthy / faulty node-steps |
| PDR | Packets arriving before run end / all generated application samples, including quarantined samples |
| Data reliability | Accepted readings within 2°C of truth / accepted readings |
| Reliable yield | Correct accepted readings / all generated application samples |
| Availability | Node-steps with a computed route / all node-steps; this is **topological route availability**, not guaranteed service uptime |
| Detection latency | Time from a node's first injected fault to its first nonhealthy state, conditional on detection |
| Recovery time | Time after the scheduled fault interval ends to healthy state, conditional on actual fault-time quarantine and observed recovery |
| Control overhead | Diagnostic requests, delivered replies and route-update message estimates per generated sample |
| Computation | Measured simulator step computation time on the host, including instrumentation |
| Radio resource estimate | 0.12 mJ × counted data attempts and control packets; an illustrative accounting model, not measured hardware energy |

Detection time is node-level first detection, not per intermittent episode. Recovery
means exclude censored nodes; `undetected_nodes`, `unrecovered_nodes` and
`quarantined_faulty_nodes` in raw results must be reported alongside conditional
means. FPR deliberately includes recovery-state occupancy after a fault ends.
Accuracy is dominated by healthy node-steps in these sparse-fault scenarios.

Packets pending at run end remain `in_flight_at_end` and count against PDR. Raw
packet latency is also recorded. High PDR alone does not prove acceptable latency.
Control traffic has a deliberately simple delivery model; all methods get the same
management-channel instrumentation. Source suppression, radio collisions, gateway
failover and arbitrary physical partitions should be studied further.

## Statistical analysis

For each size/scenario/method, report the mean, sample standard deviation and 95%
Student-t interval across run-level values. Missing/undefined quantities remain
null; their observed sample count is included. No zero is substituted for an
undefined FNR in a fault-free scenario. Intervals are not clipped to [0,1].

Compare paired adaptive-minus-baseline run-level differences for reliable yield,
FPR and PDR. Report mean paired difference, its 95% t interval and two-sided paired
Wilcoxon signed-rank p-value. All-zero differences receive p=1. Apply Holm correction
across the entire declared family (162 comparisons). These tests quantify behavior
under this simulator's model; small p-values do not establish novelty, practical
importance or real-world validity.

`compute_seconds` is affected by concurrent processes and machine load. It is a
rough host resource measure and must not be used to claim a precise speedup between
methods. Optimization correctness is tested against the reference router; a
separate profile identifies computational hotspots.

## Artifacts and provenance

- `raw/runs.jsonl` and `raw/runs.csv`: every run and every metric.
- `processed/summary.json` / `.csv`: mean, SD, interval and sample count.
- `processed/comparisons.json`: paired effects, p-values and Holm corrections.
- `figures/benchmark-{20,50,100}.png`: automatically rendered comparisons.
- `manifest.json`: run configuration, software versions and SHA-256 provenance.

Raw numerical results are generated from simulation, never written by hand.
Deterministic tests compare repeated seeds excluding host timing. Formatting-only
source changes, if recorded in the manifest, are verified by identical Python ASTs;
no behavior change is silently associated with an older result set.

Ablations and stress tests beyond the committed baseline suite are future work:
correlated faults, non-grid topologies, a failed diagnostic channel, asynchronous
clocks, varying event boundaries, mobility, workload congestion and hardware energy.
The engine exposes context/recovery flags for controlled future ablations, but no
unrun ablation result is claimed.
