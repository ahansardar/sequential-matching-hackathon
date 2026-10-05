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
