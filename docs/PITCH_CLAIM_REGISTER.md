# LuminaX pitch claim register

Use this file to keep the spoken pitch, deck, report, and repository aligned.

| Pitch claim | Exact wording | Source |
|---|---|---|
| Submitted method | The submitted method is `adaptive_greedy`. | `ROUND2_SUBMISSION.md`, section 1; `results/round2_summary.json` |
| Primary score | The public primary score is 0.4444 MSMI per 100 arrived members. | `results/round2_summary.json` |
| Greedy baseline | Greedy scores 0.3889 on the same public matrix. | `results/round2_summary.json` |
| No-ask baseline | No clarification scores 0.1389. | `results/round2_summary.json` |
| Random baseline | Random feasible scores 0.2778. | `results/round2_summary.json` |
| Outcomes | Submitted policy records 16 MSMI outcomes; greedy records 14. | `ROUND2_SUBMISSION.md`, section 6 |
| Evidence matrix | Each method has 18 episodes: 3 seeds by 6 scenario families. | `results/round2_summary.json` |
| Difference from greedy | Mean paired difference is +0.0556. | `results/round2_summary.json` |
| Uncertainty | Seed-grouped 95% interval is 0.0000 to 0.0833. | `results/round2_summary.json` |
| Sparse weakness | Submitted sparse-scenario mean is 0.0000. | `results/round2_summary.json` |
| Coverage | Submitted coverage is 0.3700; greedy coverage is 0.3717. | `results/round2_summary.json` |
| Service | 1,332 of 3,600 members are served at least once across the 18 submitted-policy episodes. | `results/round2_summary.json` |
| Wait | Median first-service wait is 5 days; p90 is 16 days. | `results/round2_summary.json` |
| Tests | The report-freeze suite contains 125 tests. | `ROUND2_SUBMISSION.md`, section 7 |
| Data validation | All 71 public data files validate. | `ROUND2_SUBMISSION.md`, section 7 |
| Container | Recorded pinned-container check has 120 calls and a 1.246-second maximum. | `results/container_check.json`; `ROUND2_SUBMISSION.md`, section 8 |
| Release | Immutable release tag is `round2-final-v2`. | Git tag; `README.md` |
| Limits | Public results do not estimate or guarantee the private score. | `results/round2_summary.json` |
| Walkthrough | Slide 5 is a fictional worked example of the submitted control flow, not a measured episode. | `ROUND2_SUBMISSION.md`, sections 3.2 to 3.5; `adaptive.py` |

## Claims not to make

- Do not say that 0.4444 is a percentage or a probability.
- Do not say the method is guaranteed to beat greedy on private worlds.
- Do not say the score is calibrated.
- Do not say the method is globally optimal.
- Do not say the simulator proves real-world dating effectiveness.
- Do not say the policy establishes demographic fairness.
- Do not say all edge cases are impossible. Say the tested boundary is broad
  and name the remaining limitations.
