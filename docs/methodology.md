# Methodology and model specification

## Evidence accumulation

For each node and each dimension, initialize positive evidence A=9 and negative
evidence B=1. The trust score is T=A/(A+B). For observable quality q in [0,1]:

```text
A' = 1 + 0.95 × (A − 1) + q
B' = 1 + 0.95 × (B − 1) + p × (1 − q)
```

Penalty p is 3 for sensing and 6 for communication. This is a discounted evidence
score inspired by success/failure counts, **not a calibrated posterior probability**:
fractional quality and asymmetric penalties do not establish Bayesian calibration.
Missing sensing evidence leaves sensing trust unchanged. Missing expected diagnostic
replies reduce communication trust. The two scores are never averaged to decide
whether a faulty sensor may relay traffic.

## Sensing evidence and context

Only received, valid observations with latency at most 1000 ms can supply fresh
sensing evidence. Snapshot peer eligibility before each update prevents dependence
on node iteration order. Eligible witnesses have sensing trust at least 0.65 and
are not sensing-isolated. Require at least two fresh eligible neighbors.

Compute the neighbor median and scaled median absolute deviation. Clamp the robust
scale to [0.5,2.0] °C; use three times that scale as the residual threshold. At least
two witnesses within 1.5°C of the subject support a coherent neighborhood. Such
support can preserve a reading even at an event boundary whose median includes
unchanged neighbors. A coherent jump exceeding 3°C from the subject's preceding
reading generates an environmental-change event. Other consistent readings obtain
positive evidence; unsupported deviations obtain negative evidence.

When witnesses are insufficient, record uncertainty and do not invent a sensing
failure. This abstention also means isolated faults can evade sensing classification
in sparse/partitioned neighborhoods. Simultaneous correlated faults can look like
an environmental event; the method cannot fundamentally identify their cause from
agreement alone. Humidity is transported/displayed but is not currently used in
context classification.

## Communication evidence

A missing diagnostic response has q=0. A received response with observed round-trip
latency L milliseconds has q=clip(1−L/2000,0,1). Responses arrive via scheduled events;
late responses cannot influence the controller before arrival. The live gateway
cannot measure synchronized one-way delay from uptime, so live communication trust
uses arrival freshness, explicitly without a latency claim.

## State transitions and reintegration

For the adaptive method: healthy/suspicious nodes become isolated below 0.4,
suspicious below 0.7, otherwise healthy. An isolated dimension may enter recovering
only when its score reaches 0.75 and at least five consecutive observations have
quality >=0.8. Recovering resets that counter and requires five more good samples
to rejoin. Quality below 0.5 during recovery immediately restores isolation.
Uncertain sensing observations interrupt the good-evidence streak.

The static baseline uses a fixed 2°C neighbor threshold and temporal jump check,
no coherent-event exemption, immediate exclusion and immediate re-admission. It
has no accumulated-score hysteresis. The conventional baseline makes no sensing
trust exclusions and uses shortest geometric paths. All methods share identical
instrumented diagnostic opportunities, exogenous disturbances and physical graph.

## Routing objective

For edge u→v, cost is geometric length plus 2×(1−communication_trust[v]); gateway
trust is one. Conventional routing uses geometric length only. Isolated/recovering
nodes are excluded as relays, while source eligibility remains a separate decision.
No alternate path is reported as an empty route. Sensing-quarantined nodes do not
originate critical data; their diagnostic observations continue.

## Ground truth and causality

The environment starts near 27°C/58% RH, with a mild spatial gradient, smooth
sinusoidal drift and ±0.2°C measurement noise. Nominal link loss is 1.5%; successful
nominal transit latency is 15–40 ms. Baseline and adaptive runs use the same seeds.
Random draws are keyed by seed/time/source/link/attempt rather than policy-dependent
random-number consumption. Consequently an identical transmission opportunity has
the same outcome across methods; changed routes naturally encounter other links.

Faults run from step 40 through 139 in the final suite (80–280 simulated seconds),
with 240 total two-second steps. Sensor bias is +15°C; random noise is ±12°C;
packet loss is 70%; high latency is 6000 ms; complete failure drops transmissions;
intermittent bias alternates in eight-step blocks. Multiple failure combines one
biased sensor with two failed nodes. Environmental events add 15°C to the top-left
2×2 physical region. Fault labels identify injected node faults, including noisy
samples that happen to land near the true value. Correct-data evaluation separately
requires absolute temperature error <=2°C.

## Scope of adaptation and limitations

Adaptive residual thresholds, discounted evidence, contextual admission and
controlled recovery are implemented. Trust-state thresholds themselves are fixed
and must not be called learned/adaptive thresholds. There is no training data,
custom ML model, blockchain, distributed consensus or authenticated trust protocol.
Radio interference, finite battery depletion, physical sensing physics, mobility,
malicious identities, compromised gateway and real environmental datasets remain
outside this prototype. These limitations constrain every result and proposed
technical advantage.
