# Decision log

Record decisions that affect the hypothesis, evaluation contract, dependencies or
submission. Add new entries; do not rewrite past decisions after results exist.

## D-001: Preserve the official starter as an upstream remote

- **Status:** accepted
- **Date:** 5 October 2026
- **Decision:** Team development happens in a separate repository. The official
  repository is retained as `upstream` for public corrections.
- **Reason:** The team has read-only access to the starter and needs private
  branches, peer review and a controlled public submission freeze.

## D-002: Enforce LF for checksum-covered data

- **Status:** accepted
- **Date:** 5 October 2026
- **Decision:** Use `.gitattributes` to keep published text data in LF form on all
  operating systems.
- **Reason:** On Windows, global automatic CRLF conversion changes file bytes and
  makes `verify_data.py` fail even though the logical records are unchanged.

## D-003: Initial policy direction

- **Status:** proposed; validate before Round 1 freeze
- **Date:** 5 October 2026
- **Decision:** Test value-of-information clarification plus uncertainty-aware
  reciprocal edge values and improved batch allocation against the supplied
  baselines.
- **Reason:** These components directly target the observed weaknesses of the
  starter and support clear hypothesis-driven ablations.

## D-004: Implement CAVIA as an auditable dependency-free prototype

- **Status:** accepted for initial experiments
- **Date:** 6 October 2026
- **Decision:** Implement targeted hard-constraint asks, uncertainty-aware
  reciprocal edge scoring, mature-feedback buckets and deterministic two-edge
  allocation improvements using only the Python standard library.
- **Reason:** This produces a complete testable policy while keeping inference
  fast, offline and easy to audit. Exact global matching and trained weights
  remain later experiments, not current claims.

## D-005: Replace CAVIA with guarded maximum-cardinality allocation

- **Status:** accepted as current competition policy
- **Date:** 7 October 2026
- **Decision:** Keep the supplied clarification and compatibility rules. Compare
  the greedy batch with a maximum-cardinality batch, and accept the alternative
  only when it adds pairs without lowering total observed compatibility.
- **Reason:** CAVIA scored below greedy on the public comparison. A more complex
  adaptive policy improved the public score but failed independent-seed
  validation. The guarded policy tied greedy's public primary score, improved
  the public mutual-acceptance tie-break and scored 0.542 versus 0.525 across ten
  independent seeds.

## D-006: Keep safe-cardinality after broader algorithm search

- **Status:** accepted as final selection for this experiment pass
- **Date:** 7 October 2026
- **Decision:** Keep `adaptive` as the submission default. Retain parallel
  matched-seed evaluation tooling, but remove rejected scoring, feedback and
  clarification candidates from the runtime image.
- **Reason:** Goal-only scoring won a ten-seed screen but lost the untouched
  twenty-seed holdout. A response-history tie-break tied the public score and
  improved two experiment blocks, but lost the final untouched holdout. Across
  300 paired independent episodes its estimated primary lift was only 0.0133,
  with a 95% normal interval from -0.0200 to 0.0467. The interval includes zero.
  The simpler safe-cardinality method remains the more defensible choice for
  unseen private worlds. Full selection figures are in
  `results/algorithm_selection_summary.json`.

## D-007: Do not promote the learned outcome scorer

- **Status:** rejected for submission runtime
- **Date:** 7 October 2026
- **Decision:** Keep the offline trainer and fitted asset for reproducibility,
  but keep `adaptive` as the submission default and leave the learned scorer
  out of the Docker image.
- **Reason:** The trainer used 18,149 valid introductions from 240 declared
  synthetic episodes. The history model won its 60-episode tuning screen but
  lost a 120-episode untouched holdout by 0.0917 MSMI per 100. The static model
  won one 120-episode holdout by 0.0250, then lost a second untouched block by
  0.0417. The apparent lift did not repeat. Full figures are in
  `results/learned_model_selection_summary.json`.

## D-008: Reject the second advanced-policy search

- **Status:** rejected for submission runtime
- **Date:** 7 October 2026
- **Decision:** Keep `adaptive` as the default and remove the experimental
  policies from the executable interface.
- **Reason:** We tested learned acceptance ranking, response history, scarcity,
  extra soft questions, exact maximum-weight matching, relationship-goal
  scoring, combined constraint-and-goal questions, and a transparent
  full-funnel score. Small tuning gains did not survive untouched seeds. On the
  ten-seed holdout, the current policy scored 0.475 MSMI per 100 arrived
  members. Goal plus history scored 0.433, and full-funnel scoring plus history
  scored 0.383. The current policy therefore remains the best validated choice.
  Raw research outputs remain local under `results/` and are not runtime inputs.

## D-009: Keep safe-cardinality after the 0.9 target search

- **Status:** accepted
- **Date:** 7 October 2026
- **Decision:** Keep `adaptive` as the submission default. Retain the legal
  observable-policy search runner, but do not add a history, waiting,
  zone-targeting or two-phase bandit component to the runtime.
- **Reason:** A 32-policy screen found a small response-history candidate, but
  it lost the final 240-episode matched comparison. Safe-cardinality scored
  0.2875 MSMI per 100 arrived members and the history candidate scored 0.2458.
  Zone-focused questions and two-phase exploration also lost their screens.
  A small five-seed block reached 0.833, showing that isolated high scores are
  unstable. Full details are in `docs/SCORE_TARGET_ANALYSIS.md`.

## D-010: Promote the day-20 guarded-history tie-break

- **Status:** accepted as current competition policy
- **Date:** 7 October 2026
- **Decision:** Keep the existing clarification, reciprocal feasibility and
  guarded maximum-cardinality allocation. From day 20, add Bayesian-smoothed
  response and acceptance history as a small secondary pair signal. Preserve
  the previous method as `adaptive_legacy` for ablation.
- **Reason:** An ungated history candidate failed an earlier confirmation, so
  it was not promoted. Adding a day-20 maturity gate scored 0.5000 versus
  0.4750 for the previous method on a 60-episode screen, then 0.2708 versus
  0.2500 on a fresh 120-episode holdout across all six variants. The repeated
  gain is modest. It also lost 0.3611 versus 0.3889 on the much smaller
  18-episode public block. The mixed result does not guarantee a private score
  or competition win.

## D-011: Reject the pair scorer and expected-unlock clarification

- **Status:** rejected for submission runtime
- **Date:** 7 October 2026
- **Decision:** Keep `adaptive` unchanged. Retain the observable search
  configurations and tests, but do not add the pair-specific funnel scorer,
  expected-unlock asks or conservative pair formula to `policy.py`.
- **Reason:** The funnel variants lost their first matched screen. Expected-
  unlock asks won a 30-episode screen by 0.1333, then lost a fresh 60-episode
  confirmation by 0.0500. The pair formula tied its screen and won a fresh
  confirmation by 0.0167, then lost the 120-episode final holdout by 0.0417.
  Full results are in `docs/PAIR_SCORER_EXPERIMENT.md`.

## D-012: Keep the incumbent after objective-separation tests

- **Status:** rejected for submission runtime
- **Date:** 7 October 2026
- **Decision:** Keep `adaptive` as the submission default. Retain the raw-
  compatibility invariants and paired confidence-audit tooling, but do not
  expose the tested `adaptive_precise` or `adaptive_raw_guard` challengers in
  the executable interface.
- **Reason:** On seeds 5201-5210 across all six variants, the fully separated
  challenger scored 0.2750 versus 0.2833 for the incumbent. Its paired 95%
  bootstrap interval was -0.0250 to 0.0000. The isolated raw-compatibility
  guard tied the incumbent at 0.2833 and tied coverage, but reduced mutual
  acceptances per 100 from 5.2583 to 5.2417. Neither challenger passed the
  promotion rule.

## D-013: Bound history and reject missing-field credit

- **Status:** accepted for submission runtime
- **Date:** 8 October 2026
- **Decision:** Clip each member's history contribution to -20 through 20. Keep
  equal observed soft-field counts and the existing clarification rule. Add
  allocation telemetry and report the paired confidence interval.
- **Reason:** The bound guarantees that history cannot override one full
  compatibility-point difference. It does not bind during valid public
  episodes. A missing-field credit of 0.25 won a 30-episode screen by 0.0333,
  then lost a fresh 60-episode confirmation by 0.0500. Credit 0.50 lost its
  screen. The day-20 history holdout gain has a paired 95% bootstrap interval
  from -0.0167 to 0.0583, so the report now labels the gain uncertain. On a
  separate 18-episode telemetry block, global allocation ran on 4.45% of days
  with at least one feasible edge.

## D-014: Retract history and guarded-cardinality promotion

- **Status:** accepted for the corrected submission runtime
- **Date:** 10 October 2026
- **Decision:** Make `adaptive_greedy` the container default. Keep the history
  and guarded-cardinality modes only as named research ablations.
- **Reason:** When all six variants from a generated seed are resampled as one
  cluster, the 20-seed history difference is 0.0208 MSMI per 100 with a 95%
  interval from -0.0375 to 0.0792. On a fresh no-history allocation block,
  guarded cardinality ties greedy at 0.2750 MSMI per 100 but has lower coverage
  (0.32825 versus 0.32867), the next official tie-break. It shortens median
  first-service wait by 0.175 days, which is reported as a service trade-off
  rather than evidence of better completed outcomes.

## D-015: Remove input-order dependence from submitted clarification

- **Status:** accepted as a correctness correction
- **Date:** 10 October 2026
- **Decision:** In the submitted `adaptive_greedy` mode, order incomplete
  members by arrival day and then opaque member ID before spending the hard-
  constraint ask budget. Keep `adaptive_input_order_greedy` only for the
  matched comparison. Do not use member IDs as predictive features.
- **Reason:** Reordering the same observable member records used to change who
  received a question. The stable rule returns identical actions across 120
  order-only permutations and keeps the same ask cost. On 20 fresh seed groups
  across all six variants, it changed MSMI by +0.0208 per 100, with a 95%
  seed-grouped interval from -0.0958 to 0.1417. That score effect is uncertain;
  this is an order-invariance correction, not a claimed performance win.

## D-016: Re-run organiser-facing diagnostics on the submitted mode

- **Status:** accepted
- **Date:** 10 October 2026
- **Decision:** Run directional calibration and profile-completeness service
  audits with `adaptive_greedy`, the actual container default. Add equal-
  variant calibration, paired seed-clustered Brier differences, completeness
  and opportunity subgroups, and arrival-by-opportunity service cells.
- **Reason:** The first corrected evidence package explicitly called the old
  `adaptive` research mode. Careful statistics on the wrong policy would not
  answer the organiser's question about the submitted method.
