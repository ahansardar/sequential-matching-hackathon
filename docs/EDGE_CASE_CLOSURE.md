# LuminaX 33-item closure register

This is the fixed closure boundary requested on 10 October 2026. A row is
closed only as one of:

- `fixed`: code, validation or a repeatable test enforces the answer;
- `measured`: a matched experiment was run and the result was accepted or
  rejected without changing the submission claim; or
- `contract-excluded`: the published observable request cannot identify the
  quantity, so the policy does not claim to solve or use it.

No item below is pending.

| # | Concern | State | Closure evidence |
|---:|---|---|---|
| 1 | Subgroup uncertainty | fixed | Profile-service and directional-calibration subgroup intervals resample whole seed worlds. |
| 2 | Tiny subgroup instability | fixed | Counts are retained and calibration cells below 200 examples are suppressed rather than interpreted. |
| 3 | Wait-time survivorship bias | fixed | Decision-window burden includes served and never-served members through day 60. |
| 4 | Repeated-service concentration | fixed | Service output records zero, one and two-or-more introductions plus the maximum for one member. |
| 5 | Available-time differences | fixed | Service rates use available-member-days as an exposure denominator. |
| 6 | Opportunity changes after arrival | fixed | Observable opportunity is measured on every available day, not only at arrival. |
| 7 | Holdout reuse | fixed | The permanent seed ledger assigns every declared seed range a role and rejects accidental overlap. |
| 8 | Small number of independent worlds | fixed | Exact sign-flip, leave-one-seed-out and approximate detectable-effect checks accompany the clustered intervals. |
| 9 | Contradictory member records | fixed | Inconsistent field value, status or observation day makes the member unusable instead of guessed. |
| 10 | Conflicting introduction records | fixed | Data validation rejects duplicate IDs, repeated pairs, invalid endpoints and wrong deadlines. |
| 11 | Orphan feedback | fixed | Every feedback event must reference an existing introduction and one of its endpoints. |
| 12 | Impossible funnel stages | fixed | Responses, dates, second intentions and pauses must follow the allowed event sequence. |
| 13 | Exact deadline contract | fixed | Every introduction deadline must equal assignment day plus seven. |
| 14 | Odd population sizes | fixed | Tests cover 1, 3, 199 and 201 available members and enforce floor(n/2) disjoint pairs. |
| 15 | Highly imbalanced pools | fixed | Tests cover singleton sides and a graph with exactly one feasible reciprocal pair. |
| 16 | Computationally hostile valid requests | fixed | A near-1 MiB request with long constraint arrays is exercised through the real process boundary. |
| 17 | Maximum per-call latency | fixed | Evaluation records maximum and p95 policy-call time; the boundary test requires every call below ten seconds. |
| 18 | Same-day state transitions | fixed | Match decisions use the refreshed match-phase state and cannot reuse members made unavailable after asking. |
| 19 | Opaque-ID tie starvation | measured | Arrival-priority equal-score ties lost the matched comparison and worsened p90 wait, so they were rejected. |
| 20 | One remaining unmatched member | measured | Odd-size tests enforce valid output; concentration and decision-window burden expose who remains unserved. |
| 21 | Early matching versus waiting | measured | The waiting-policy search failed confirmation and remains outside the runtime. |
| 22 | Unused clarification budget | measured | Extra-question and two-phase searches failed confirmation and remain outside the runtime. |
| 23 | Sparse-pool collapse | fixed | Empty, singleton and one-edge states return valid deterministic outputs; every study includes the sparse variant. |
| 24 | Service versus score conflict | fixed | Promotion follows MSMI first and the published tie-break order; service measures are reported separately. |
| 25 | Calibration before and after drift | fixed | Assignment-day bands 0-19, 20-34 and 35-59 have metrics and seed-clustered intervals. |
| 26 | Intersectional calibration | fixed | Profile completeness, opportunity and assignment time are crossed, with small cells suppressed. |
| 27 | Calibration-bin sensitivity | fixed | Equal-count ECE is recomputed with 5, 10 and 20 bins. |
| 28 | Assignment-selection bias | contract-excluded | Outcomes exist only for assigned pairs. The report limits calibration claims to those pairs and makes no counterfactual claim about unassigned pairs. |
| 29 | Rare-outcome instability | fixed | Raw event counts remain in episode outputs and all intervals cluster by independent seed world. |
| 30 | Multiple algorithm search | measured | The seed ledger separates study roles; negative challengers are recorded and the final mode is not selected from one lucky block. |
| 31 | Markdown, PDF and result parity | fixed | The release audit checks cited result files plus both Markdown and PDF SHA-256 values against the sidecar. |
| 32 | Dashboard staleness | fixed | The dashboard export declares `adaptive_greedy`, and a unit test locks it to the container default. |
| 33 | Remote-link availability | fixed | One manifest release tag is used by the reply and report. Optional HTTPS verification reports unavailable networking without requiring Git or crashing. |

The register closes engineering and evidence-handling risks within the
published simulator contract. It does not promise a private score, real-world
generalisation or selection by the organisers.
