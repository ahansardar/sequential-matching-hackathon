# Team contribution guide

This repository is a two-person competition workspace derived from the official
Sequential Matching Problem starter. Keep the official release available as the
`upstream` remote and make team changes through short-lived branches and pull
requests.

## First-time setup

Requirements: Git and Python 3.10 or later. The starter has no third-party Python
dependencies.

```powershell
python -m unittest -v
python verify_data.py
python evaluate.py --seeds 101 --output results/smoke.json
```

If `python` is not available on Windows, use `py` in the same commands.

## Branch and review workflow

1. Synchronise `main` before starting work.
2. Create one focused branch named `research/<topic>`, `policy/<topic>`,
   `experiment/<topic>`, `docs/<topic>` or `fix/<topic>`.
3. Keep commits small and explain why the change helps the hypothesis.
4. Open a pull request. The teammate who did not author it reviews it.
5. Merge only after required checks pass and experimental claims are backed by
   committed or linked machine-readable results.

Do not commit directly to `main`. Prefer squash merges for focused changes and
use a normal merge when preserving a meaningful experiment history.

## Definition of done

- The JSON ask/match protocol remains valid, including empty populations.
- No hidden simulator fields, future data, generator seeds or private organiser
  files are read by the policy.
- Hard reciprocal feasibility is checked before scoring or allocation.
- Tests pass and `verify_data.py` succeeds.
- A smoke evaluation completes without an invalid episode.
- Any policy comparison uses identical seeds and variants.
- Results state whether they are exploratory, validation or development-test.
- New dependencies are pinned, licensed and usable offline in the submitted
  container.
- Logs and documentation do not contain credentials or personal data.

## Experiment discipline

Use the supplied split as intended:

- `public_01` to `public_06`: training and method development.
- `public_07` and `public_08`: validation and model selection.
- `public_09` and `public_10`: development test; avoid repeated tuning on these.

Simulator experiments must declare their seeds. Compare the team policy against
`greedy`, `no_asks` and `random` on the same seed/variant matrix. Do not select
only favourable runs. Commit final result JSON explicitly because `results/` is
ignored by default.

## Keeping the starter current

Fetch official corrections without pushing team work to the starter repository:

```powershell
git fetch upstream
git log --oneline main..upstream/main
```

Review `CHANGELOG.md` before integrating an upstream update. Resolve changes in a
dedicated `chore/upstream-sync` branch and rerun the full verification sequence.
