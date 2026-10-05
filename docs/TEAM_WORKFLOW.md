# Two-person team workflow

## Working agreement

Use pull requests for every change to `main`. One teammate owns a task; the other
reviews its assumptions, correctness and evidence. Ownership is temporary and
does not prevent either teammate from contributing to the same area.

| Track | Primary responsibility | Reviewer responsibility |
|---|---|---|
| Research and modelling | State hypotheses, features, uncertainty and ablations | Challenge leakage, target definition and evidence |
| Policy engineering | Maintain ask/match protocol, allocation and memory | Review feasibility, limits and edge cases |
| Experiments | Run fixed seed/variant matrices and retain raw JSON | Check fairness, split usage and interpretation |
| Submission | Assemble report, immutable commit and verification evidence | Re-run commands from a clean clone |

For the first pass, one person should lead research/experiments while the other
leads policy engineering. Swap reviews so both people understand the complete
submission.

## Milestones

### 5-6 October: reproduce and choose the hypothesis

- Verify the starter, data contract and all three supplied baselines.
- Write the Round 1 hypothesis and define the ablation before implementation.
- Decide how clarification value and global allocation will be measured.

### 7-8 October: research note and feasibility prototype

- Produce scenario-level exploratory results on declared seeds.
- Stress-test sparse, cold-start, delayed and drift conditions.
- Freeze the Round 1 Markdown/PDF candidate early enough for peer review.

### 9 October: Round 1 submission

- Recheck every required topic in `docs/SUBMISSION.md`.
- Submit through the organiser's Google Form by 23:59 IST.
- Save the submission receipt and a frozen copy of the submitted document.

### 12-16 October: build and ablations

- Implement the selected policy behind the unchanged JSON interface.
- Run baseline and ablation matrices on identical seeds and all six variants.
- Add policy-specific unit tests and container checks.

### 17-18 October: freeze and submit

- Re-run from a clean clone, including the offline Docker path.
- Commit the report, full result JSON, inference assets and licences.
- Pin the public submission to a full 40-character commit SHA before 23:59 IST.

## GitHub settings to enable

Once both teammates have repository access:

- Keep the team repository private during development; make the final submitted
  source publicly accessible before the deadline.
- Protect `main`: require a pull request, one approval and passing checks.
- Disable force pushes and branch deletion on `main`.
- Add both teammates as repository collaborators with write access.
- Use Issues for tasks and PRs for code/research review; do not use the organiser
  repository's public Issues for internal team planning.

## Coordination rules

- Assign an Issue before beginning work to avoid duplicate experiments.
- Put the exact command, commit and seed list on every experiment Issue.
- Never edit a result JSON by hand.
- Record methodological decisions in `docs/DECISIONS.md`.
- Treat an upstream rules change as a blocking review item for both teammates.
