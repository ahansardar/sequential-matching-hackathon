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
