# Round 1 experiment plan

## Purpose

The experiments should answer one question: does the proposed method improve the
decision policy, and which component is responsible?

Round 1 can be submitted without a finished implementation. Do not invent team
results. Use this plan to produce preliminary evidence only if time allows.

## Methods to compare

| ID | Method | Purpose |
|---|---|---|
| B1 | Greedy | Main supplied baseline |
| B2 | No asks | Measures the value of clarification |
| B3 | Random feasible | Measures the value of pair ranking |
| T1 | Full team policy | Proposed complete method |
| A1 | Team policy with starter asks | Clarification ablation |
| A2 | Team policy with greedy allocation | Allocation ablation |
| A3 | Team policy without uncertainty penalty | Missingness ablation |

## Scenario families

Every serious comparison must include all six variants:

- `development`
- `sparse`
- `cold_start`
- `delayed`
- `shift`
- `drift`

## Seed plan

Use fixed, declared seed groups. Do not change a seed group after looking at its
results.

| Stage | Seeds | Use |
|---|---|---|
| Smoke | `101` | Check that the process and result format work |
| Development | `101,102,103,104,105` | Build and debug the method |
| Validation | `201,202,203,204,205` | Select between method variants |
| Final confirmation | `301,302,303,304,305` | Run once after choices are frozen |

These simulator seed groups are separate from the ten static data pools. For the
static data, use `public_01` to `public_06` for development, `public_07` and
`public_08` for validation, and reserve `public_09` and `public_10` for final
development checks.

## Supplied baseline commands

Start with a one-seed smoke test:

```powershell
python evaluate.py --baseline greedy --seeds 101 --variants all --output results/greedy_smoke.json
python evaluate.py --baseline no_asks --seeds 101 --variants all --output results/no_asks_smoke.json
python evaluate.py --baseline random --seeds 101 --variants all --output results/random_smoke.json
```

Then run the development matrix:

```powershell
python evaluate.py --baseline greedy --seeds 101,102,103,104,105 --variants all --output results/greedy_development.json
python evaluate.py --baseline no_asks --seeds 101,102,103,104,105 --variants all --output results/no_asks_development.json
python evaluate.py --baseline random --seeds 101,102,103,104,105 --variants all --output results/random_development.json
```

The exact team-policy command will be added when its executable entry point is
implemented. It must use the same seed and variant lists.

## Metrics to save

Keep the full evaluator JSON. The summary table should contain:

| Metric | Why it matters |
|---|---|
| MSMI per 100 arrived members | Primary competition score |
| Distinct-member coverage | First tie-breaker and service reach |
| Mutual acceptances per 100 | Second tie-breaker and funnel stage |
| Clarification cost | Third tie-breaker |
| Inference time | Fourth tie-breaker and execution risk |
| Assignments and dates | Explains the outcome funnel |
| Missing feedback | Prevents false rejection claims |
| Waiting time and unserved count | Shows who the policy leaves behind |
| Invalid episodes | Any assessed invalid episode is disqualifying |

## Fair comparison rules

1. Use the same seeds and variants for every compared method.
2. Do not choose only seeds where the team method wins.
3. Do not use unresolved outcomes as completed failures.
4. Do not use future or hidden simulator information.
5. Record the exact Git commit for every important run.
6. Never edit result JSON by hand.
7. Report zero scores and failures.
8. Separate development, validation and final-confirmation results.

## Result table template

| Method | Variant | Seeds | MSMI/100 | Coverage | Mutual/100 | Ask cost | Runtime | Invalid |
|---|---|---|---:|---:|---:|---:|---:|---:|
| Greedy | development | [TODO] | [TODO] | [TODO] | [TODO] | [TODO] | [TODO] | 0 |
| Team policy | development | [TODO] | [TODO] | [TODO] | [TODO] | [TODO] | [TODO] | 0 |

Add one row per method and scenario. Include variation across seeds, not only the
mean, when writing the final report.

## Interpretation rules

- A larger score on one seed is not enough to claim improvement.
- Similar coverage does not mean similar match quality.
- A lower ask cost matters only after the primary outcome and earlier tie-breakers.
- A zero MSMI result may be caused by a small number of downstream events.
- Simulator performance is not evidence of real-world relationship success.
