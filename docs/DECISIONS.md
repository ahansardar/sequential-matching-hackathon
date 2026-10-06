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
