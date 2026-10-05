# Private technical disclosure notes — preliminary

**Candidate research mechanism only.** No patentability, novelty, freedom-to-operate,
legal-status or publication outcome is asserted. Keep this document and repository
private. The user has authorized saving code to the specified private GitHub repo;
that does not authorize a public repository, public Wokwi project or publication.

## Technical problem and proposed mechanism

Faulty measurements, unreliable forwarding and genuine environmental changes can
require different responses. This prototype separates the evidence/state that
controls measurement admission from the evidence/state that controls relay usage.
Fresh neighborhood context can preserve coherent observations, while isolated
components continue to be probed and must demonstrate sustained positive evidence
before re-admission.

## Technical effects requiring support

Potential effects include avoiding unnecessary relay removal after a sensing fault,
preserving useful event data and restoring participation without rapid oscillation.
Measured effects are limited to the included synthetic experiments. Higher
false-positive occupancy and slow reintegration are material contrary evidence.

## Features for a future claim chart, not drafted legal claims

- Separate evidence accumulators tied to different network control actions.
- A freshness/witness eligibility rule and coherent-context admission decision.
- A monitored isolation/probation/re-admission sequence.
- An explicit budgeted diagnostic path sustaining recovery observations.

A qualified IP review would need to determine whether a narrowly specified
combination differs from existing claims and literature. Broad claims to trust,
neighbor validation, routing around failures or recovery are inappropriate given
known prior art. See the linked records in `research-gap.md`; their current legal
status is not evaluated here.

## Filing/disclosure decision record

No patent has been filed, no paper submitted, no publication made and no legal
claim drafted by this implementation. Before external disclosure, obtain the
appropriate institutional/IP advice, identify inventorship and ownership, inspect
relevant prior-art claims, and decide whether filing is justified. This project
makes no guarantee of Scopus indexing, acceptance or patent grant.
