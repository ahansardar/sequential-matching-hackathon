# Score target analysis

## Result

We did not find a rules-compliant algorithm that reliably scores 0.9.

The current `adaptive` policy remains the submission default. It protects every
hard constraint, tries to increase the number of daily pairs, and rejects an
alternative batch if its observed compatibility total is lower.

## What a score of 0.9 means

Each episode has 200 arrived members. One successful MSMI pair scores 0.5.
Therefore, an average score of 0.9 needs about 1.8 successful pairs in every
episode across all six scenario families.

The final outcome is rare. Both members must respond Yes, a date must happen in
time, and both members must request another meeting within three days. Several
important response tendencies are hidden from the policy.

## Algorithms tested

The search covered:

- greedy compatibility matching;
- guarded maximum-cardinality matching;
- exact maximum-weight matching;
- learned acceptance and full-funnel scores;
- relationship-goal-first scores;
- response, acceptance and second-meeting history;
- uncertainty bonuses and scarcity bonuses;
- minimum-quality waiting thresholds;
- extra soft questions and combined constraint-and-goal questions;
- zone-focused clarification for sparse geography; and
- explore-first, exploit-later bandit policies.

The reusable legal search runner is `experiments/search_observable_policy.py`.
It passes only the observable state to its decision logic and compares every
configuration on identical seeds.

## Final confirmation

We compared the current policy with the best small-screen history candidate on
20 untouched seeds in all six scenarios. That is 120 episodes per policy.

| Policy | Primary score | Coverage | Mutual acceptances per 100 |
|---|---:|---:|---:|
| Current safe-cardinality policy | 0.2875 | 0.3386 | 5.2750 |
| Light response-history policy | 0.2458 | 0.3392 | 5.3792 |

The history policy increased the acceptance tie-break slightly but reduced the
primary MSMI score. It is rejected.

A separate five-seed block gave the current policy 0.833. This did not repeat
on the larger untouched block. Small samples can look excellent because one or
two additional successful pairs move the score sharply.

## Decision

Do not claim or optimise toward a selected 0.9 result. That would be seed
cherry-picking, not a competition-ready improvement. Keep `adaptive` until a
new method beats it on a large untouched block and then repeats the gain on a
second block.
