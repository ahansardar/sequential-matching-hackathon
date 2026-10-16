# Final submission issue text

Copy this text into the organiser's Final submission issue after the final
commit is pushed. Do not replace the token by hand. Render the final text with
the release-gate command below, then test each URL in a signed-out browser
window before submitting. The final gate also requires the immutable
`round2-final-v2` tag to point to that same commit; create the tag only after
the release commit exists, and never move it.

## Team name and size

LuminaX, 2 participants.

## Public source URL and immutable version

Repository:
`https://github.com/ahansardar/sequential-matching-hackathon`

Assessed commit:
`FULL_COMMIT_SHA`

Immutable source snapshot:
`https://github.com/ahansardar/sequential-matching-hackathon/tree/FULL_COMMIT_SHA`

## Report and results URLs

Technical report:
`https://github.com/ahansardar/sequential-matching-hackathon/blob/FULL_COMMIT_SHA/ROUND2_SUBMISSION.md`

PDF report:
`https://github.com/ahansardar/sequential-matching-hackathon/blob/FULL_COMMIT_SHA/output/pdf/LuminaX_Round2_Final_Report.pdf`

Machine-readable summary:
`https://github.com/ahansardar/sequential-matching-hackathon/blob/FULL_COMMIT_SHA/results/round2_summary.json`

Release hash manifest:
`https://github.com/ahansardar/sequential-matching-hackathon/blob/FULL_COMMIT_SHA/round2_release_manifest.json`

The summary links the five complete method files for the submitted policy, the
three required baselines, and one focused ablation. Each file contains all 18 public
episodes from seeds 101, 102, and 103 across all six scenario families.

## Build and evaluation commands

```text
python -m unittest -v
python verify_data.py
python evaluate.py --baseline adaptive_greedy --seeds 101,102,103 --variants all --output results/final.json
python experiments/build_round2_summary.py --output results/round2_summary.json
docker build -t sequential-policy:submission .
python evaluate.py --image sequential-policy:submission --seeds 101 --variants development --output results/container_check.json
python experiments/build_round2_release.py --output round2_release_manifest.json
python experiments/round2_release_gate.py --commit HEAD --output results/round2_release_gate.json --render-issue tmp/FINAL_SUBMISSION_ISSUE_READY.md
```

The assessed entry point is `policy.py`. The container runs offline on CPU and
needs no credentials, network access, GPU, writable persistent storage, or
external service.

## Assets, licences, and tools

The submitted method is deterministic and has no trained model or inference
asset. It uses Python 3.12.7 standard-library modules only. Development used
Python, Git, PowerShell, and Docker Desktop. The repository includes the starter
MIT licence, synthetic-data permission, LuminaX submission licence, and
third-party notices.

Research-only model files and experimental policies are not called by the
container entry point.

## Validation and comparisons

- Submitted method: `adaptive_greedy` through the container default.
- Required baselines: `greedy`, `no_asks`, and `random`.
- Scenario families: development, sparse, cold start, delayed, shift, and drift.
- Ablation: input-order clarification without the submitted stable ordering.
- Public comparison seeds: 101, 102, and 103 for every method.
- Inference random seed: none. The submitted policy is deterministic.
- Checks: full unit suite, public data verification, complete local matrix,
  result-matrix validator, offline Docker build, container evaluation, and the
  fail-closed release gate.

The random baseline file is a deterministic assembly of valid, non-overlapping
episodes from two interrupted official evaluator runs. The source runs are
retained in the repository, duplicate valid episodes agree, and the assembly
script recomputes the summary. This provenance is disclosed because the local
host was under unrelated CPU contention during those runs.

Public simulator results test the interface and declared scenarios. They do not
guarantee the private score or performance with real people.
