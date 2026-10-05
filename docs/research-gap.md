# Preliminary prior-art analysis and candidate research gap

This is a scoped technical literature review, not an exhaustive novelty or patent
clearance search. The exact project title is not used as evidence of novelty.

| Existing approach | Established contribution | Boundary relevant to this prototype |
| --- | --- | --- |
| [Yim & Choi, 2010: Adaptive Fault-Tolerant Event Detection](https://www.mdpi.com/1424-8220/10/3/2332) | Neighbor readings and confidence-adjusted decisions distinguish events despite faults | Neighbor voting and adaptive event thresholds are established |
| [Wang & Liu, 2016: Online Fault-Tolerant Dynamic Event Region Detection via Trust](https://arxiv.org/abs/1610.02291) | Online trust combines spatial and temporal evidence for fault-tolerant event-region detection | Context-aware trust cannot itself be claimed as new |
| [SecTrust-RPL, 2019](https://www.sciencedirect.com/science/article/pii/S0167739X17306581) | Trust-aware routing, attack detection and isolation, with simulation/testbed evaluation | Trust-driven route exclusion is established; this prototype is not an implementation of RPL |
| [Secure Geographic Routing, 2010](https://link.springer.com/article/10.1155/2010/975607) | Multiple direct trust metrics and trust-aware routing | Multiple trust factors/dimensions are not automatically novel |
| [ETMRM, 2018](https://www.sciencedirect.com/science/article/pii/S1389128618301725) | Centralized trust and energy-aware routing for software-defined sensor networks | Centralized trust management and resource-aware routing are established |
| [US20080084294A1](https://patents.google.com/patent/US20080084294A1/en) | Neighbor trust management and adaptive routing around suspect nodes | Broad trust-and-reroute claims face direct prior art |
| [KR20150062136A](https://patents.google.com/patent/KR20150062136A/en) | Trust-routing detection-error recovery and intermediate trust states | Recovery and intermediate status concepts require careful claim-by-claim comparison |
| [US20250267453A1](https://patents.google.com/patent/US20250267453A1/en) | Adaptive trust recovery in mixed-environment communications | Trust restoration is not an unexplored concept |

## The proposed chain

Existing trust/event/routing mechanisms
→ the selected references do not by themselves establish the behavior of this
specific joint admission/relay/reintegration policy under the same experimental setup
→ evaluate its reliability/availability/overhead tradeoffs explicitly
→ separately control measurement admission and relay eligibility, preserve coherent
context and require observed recovery evidence
→ possible technical effect: preserve useful routes and genuine-event observations
while removing unreliable measurements.

That final effect is a **hypothesis**, not an assumption that the combination is
novel or superior. The measured prototype results show improved delivery against
the conventional baseline during complete node failure and preserved readings in
the chosen event scenario, but worse false-positive occupancy and recovery than a
static method in several cases. See `results.md`.

## Candidate differentiators to investigate

1. Coordinating sensing admission and relay eligibility rather than applying one
   overall trust threshold to both decisions.
2. Event-context preservation with explicit abstention for insufficient fresh
   witnesses, followed by monitored reintegration.
3. Evaluating the combined policy with shared disturbance opportunities, separate
   ground truth, conditional recovery statistics and reliable-yield denominators.

None of these is asserted to be unprecedented. The discounted score, robust
median/MAD, Dijkstra routing and hysteresis are familiar building blocks.

## Search coverage and remaining work

Queries targeted IEEE, Springer, ScienceDirect, ACM, arXiv, Google Scholar and
Google Patents. Primary material was accessible for the references above. IEEE
index results included SMTrust and sensor self-diagnosis work; some full text was
not accessible. ACM and direct Google Scholar coverage was limited. WIPO PATENTSCOPE
could not be fully queried through the available interface; Indian InPASS was
identified but a complete claim/database search was not performed.

Before any filing or publication: extend citation chaining, inspect full texts,
search patent families and claims across jurisdictions, document query dates and
exclusions, and build a feature-by-feature claim chart. Missing search results do
not establish absence of prior art. No database-access barrier has been bypassed.
