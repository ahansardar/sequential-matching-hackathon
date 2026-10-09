# Score target analysis

## Result

We did not find a rules-compliant algorithm that reliably scores 0.9.

The current `adaptive` policy is now the guarded-history version. It protects
every hard constraint, keeps compatibility dominant and uses mature observed
response history from day 20 onward.

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

## Earlier rejected candidate

We compared the current policy with the best small-screen history candidate on
20 untouched seeds in all six scenarios. That is 120 episodes per policy.

| Policy | Primary score | Coverage | Mutual acceptances per 100 |
|---|---:|---:|---:|
| Current safe-cardinality policy | 0.2875 | 0.3386 | 5.2750 |
| Light response-history policy | 0.2458 | 0.3392 | 5.3792 |

This ungated history policy increased the acceptance tie-break slightly but
reduced the primary MSMI score. It remains rejected.

A separate five-seed block gave the current policy 0.833. This did not repeat
on the larger untouched block. Small samples can look excellent because one or
two additional successful pairs move the score sharply.

## Gated-history confirmation

The next experiment changed one thing: history is ignored until day 20. Pair
compatibility is multiplied by 100, and smoothed response and acceptance
history is used only as a small secondary signal.

| Evaluation block | Episodes per policy | Guarded history | Previous policy | Difference |
|---|---:|---:|---:|---:|
| Seeds 3901-3910, all variants | 60 | 0.5000 | 0.4750 | +0.0250 |
| Fresh seeds 4001-4020, all variants | 120 | 0.2708 | 0.2500 | +0.0208 |
| Public seeds 101-103, all variants | 18 | 0.3611 | 0.3889 | -0.0278 |

On the fresh holdout, coverage was 0.3367 versus 0.3353 and mutual acceptances
per 100 were 5.4875 versus 5.3500. The primary gain repeated, so the gated
version replaces the previous policy. The old method remains available as
`adaptive_legacy` for direct ablation.

The much smaller public block moved in the other direction. Across these three
listed blocks, weighted by episode count, guarded history is ahead by about
0.0177 MSMI per 100. This average includes a tuning screen, so the untouched
holdout is still the main selection evidence.

## Decision

Promote the day-20 guarded-history policy because its gain repeated on a fresh
holdout. Do not claim that it will score 0.9 or guarantee a win. The measured
gain is small, one small public block favored the previous policy, and hidden
evaluation worlds may behave differently.

## Follow-up improvement search

We later tested pair-specific full-funnel scoring, expected-unlock clarification
and a conservative pair formula. The best formula won one 60-episode
confirmation but lost the final 120-episode holdout, 0.3792 to 0.4208. None was
promoted. See `docs/PAIR_SCORER_EXPERIMENT.md`.
