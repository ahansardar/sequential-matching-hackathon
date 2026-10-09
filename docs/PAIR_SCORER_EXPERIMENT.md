# Pair-specific improvement experiment

Status: rejected for the submission runtime.

We tested three ways to improve the guarded-history policy. None produced a
repeatable primary-score gain, so `adaptive` remains unchanged.

## Rules protected in every test

- The policy received only the observable request state.
- The official reciprocal eligibility check created candidate edges.
- The incumbent policy remained the fallback.
- A challenger batch could not reduce pair count or raw soft compatibility.
- Every comparison used identical seeds and scenario variants.

The rerunnable configurations live in
`experiments/search_observable_policy.py`.

## Pair-specific full-funnel score

The scorer estimated the chance of both responses, both acceptances, a date and
two on-time second-meeting responses. It used the committed model trained on
declared synthetic seeds 2001-2040. The score could only refine the incumbent
batch.

On seeds 4101-4102 across all six variants, the incumbent scored 0.2500. The
best funnel variant scored 0.2083; the other funnel variants scored 0.1667.
We stopped this branch before a larger holdout.

## Expected-unlock clarification

This policy asked the four available members whose hard-constraint answers
could unlock the most currently plausible reciprocal edges.

| Block | Episodes per policy | Expected unlock | Incumbent |
|---|---:|---:|---:|
| Seeds 4101-4105 | 30 | 0.3833 | 0.2500 |
| Fresh seeds 4201-4210 | 60 | 0.2583 | 0.3083 |

The tuning gain reversed on fresh seeds. Mutual acceptance also fell from
5.4083 to 4.8833 per 100 on the confirmation block.

## Conservative pair formula

This challenger kept raw compatibility protected, then preferred equal-
compatibility alternatives using a fixed pair formula. The formula emphasized
relationship goal, pace, lifestyle and conversation agreement. It never read
the scenario name.

| Block | Episodes per policy | Pair formula | Incumbent |
|---|---:|---:|---:|
| Seeds 4101-4105 | 30 | 0.2500 | 0.2500 |
| Fresh seeds 4201-4210 | 60 | 0.3250 | 0.3083 |
| Final seeds 4301-4320 | 120 | 0.3792 | 0.4208 |

The candidate tied the screen and won the first confirmation by 0.0167. It then
lost the larger final holdout by 0.0417. Its final-holdout coverage and mutual
acceptance were slightly higher, but MSMI is the primary competition metric.

## Decision

Do not add these challengers to `policy.py` or the Docker image. The experiment
improved our search tooling and clarified where the policy is weak, but it did
not produce a safer submission than the current guarded-history method.
