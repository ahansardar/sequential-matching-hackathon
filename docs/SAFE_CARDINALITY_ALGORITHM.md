# Guarded-history safe-cardinality policy

Status: research ablation; not the corrected container default.

The corrected 10 October addendum retracts promotion of the history and guarded
cardinality components. See `ROUND1_CORRECTED_ADDENDUM.md` and decision D-014.
The implementation remains available so the negative result is reproducible.

This policy builds on the validated safe-cardinality method. It tries to serve
more people in each daily batch. From day 20, it also uses observed response and
acceptance history to prefer reliable members when compatibility is close.

It uses no external model, API, network connection or hidden simulator value.

## Daily flow

Each day has two phases.

1. Ask up to four available people for their missing hard-constraint bundle.
2. Build the reciprocal feasible graph after the answers arrive.
3. Give each feasible pair an observed compatibility score.
4. From day 20, add a small score based on observed response and acceptance
   history.
5. Build both a greedy batch and a maximum-cardinality batch.
6. Use the maximum-cardinality batch only if it is strictly larger and its total
   policy score is at least as high as the greedy batch.

If either safety condition fails, the policy returns the greedy batch.

## Clarification

The policy keeps the supplied clarification rule. A hard-constraint bundle costs
3 units, so the 12-unit daily budget permits at most four requests.

It asks only available members who have unanswered hard constraints and no
declined hard field. A declined field stays missing, so the policy does not spend
the budget asking for it again.

We tested more complicated question policies. They improved a few public runs
but scored worse than greedy across ten independent seeds. They are not part of
the submitted policy.

## Reciprocal feasibility

The policy includes an edge only when the official `eligibility` function says
the pair is feasible.

It also removes:

- unavailable members;
- members with unknown hard constraints;
- pairs introduced previously; and
- any pair that fails either person's hard requirements.

Soft compatibility never overrides a hard constraint.

## Observed compatibility

For each feasible pair, the policy counts equal observed values across the seven
soft fields:

- relationship goal;
- relationship pace;
- lifestyle;
- conversation preference;
- emotional availability;
- space for a relationship; and
- relocation preference.

A missing field gives no point. It is not treated as agreement or disagreement.

This is the same transparent compatibility count used by the supplied greedy
baseline.

## Mature-history tie-break

Before day 20, the pair score is:

```text
100 * number of equal observed soft fields
```

From day 20, each member receives two smoothed estimates: how often they answer
an introduction, and how often an answer is Yes. The policy adds the log-odds
of those two estimates for both people:

```text
pair score = 100 * compatibility
           + history quality of person A
           + history quality of person B
```

The priors are 0.765 for response and 0.46 for acceptance, each with strength
four. They were fixed during development before the final 4001-4020 holdout.
The later training asset measured rates of 0.7592 and 0.4574 across 18,149
introductions from 240 episodes. Strength four is a hand-chosen small-sample
regularizer.

The policy clips each member's history value to -20 through 20. A pair's history
term is therefore between -40 and 40. The factor of 100 guarantees that history
cannot override one full compatibility-point difference on an individual edge.

Only feedback already present in the policy request is counted. A missing
response counts as a response trial but not a response. Acceptance is measured
only when a response exists. The policy does not use member IDs, private seeds,
future events or hidden simulator values.

## Allocation

The greedy batch takes the highest-scoring remaining edge until no additional
non-overlapping edge can be added.

The alternative batch uses Edmonds' blossom algorithm to find a maximum-
cardinality matching in the general graph. A deterministic local improvement
then raises the observable policy score without reducing the number of pairs.

The policy accepts the alternative only when both statements are true:

```text
alternative pair count > greedy pair count
alternative total policy score >= greedy total policy score
```

This guard prevents the global allocator from changing a batch merely because a
different maximum matching exists.

On seeds 5301-5303 across all six variants, the global batch ran on 26 of 1,080
decision days. It ran on 4.45% of days with at least one feasible edge. The
branch is active but uncommon.

## Why this design was selected

The earlier CAVIA prototype added targeted questions, hand-weighted pair scores,
feedback buckets and local pair exchanges. It scored 0.361 on the 18 public
episodes, below the greedy score of 0.389. A later adaptive version appeared to
score 0.500 on those episodes but fell to 0.392 against greedy's 0.525 across ten
independent seeds. We rejected both versions.

The safe-cardinality policy produced the following matched results:

| Evaluation set | Safe policy | Greedy | Finding |
|---|---:|---:|---|
| Public seeds 101-103, 18 episodes | 0.389 | 0.389 | Primary score and coverage tie |
| Public mutual acceptances per 100 | 5.64 | 5.50 | Safe policy wins the next tie-break |
| Independent seeds 1101-1110, 60 episodes | 0.542 | 0.525 | Small primary-score improvement |

We also tested goal-only scoring, outcome-weighted scoring, targeted questions
and early feedback tie-breaks. Several won small development screens and then
lost holdouts. The useful change was to delay history until day 20 and keep
compatibility dominant.

The gated version scored 0.5000 versus 0.4750 for the previous policy on its
60-episode screen. It then scored 0.2708 versus 0.2500 on a fresh 120-episode
holdout covering all six variants. This is a measured gain of 0.0208, not proof
of a private-evaluation win. On the small 18-episode public set, it scored
0.3611 versus 0.3889 for the previous policy. The larger independent evidence
favored the gated method, but the public loss shows that the gain is uncertain.
On the 120-episode holdout, a 20,000-resample paired bootstrap interval for the
score difference was -0.0167 to 0.0583. The interval includes zero.
The search details are in
`docs/SCORE_TARGET_ANALYSIS.md`.

We then trained direct and decomposed outcome models on 18,149 introductions
from 240 declared synthetic episodes. The strongest history model won tuning
but lost its untouched holdout. A simpler static model won one holdout and lost
the next. We kept both models out of the submission runtime because the gain did
not repeat. See `docs/OUTCOME_MODEL_EXPERIMENT.md` and
`results/learned_model_selection_summary.json`.

These are synthetic simulator results. They do not guarantee a private-evaluation
win or describe real relationship outcomes.

## Experiment modes

| Mode | Purpose |
|---|---|
| `adaptive` | Current guarded-history safe-cardinality policy |
| `adaptive_legacy` | Previous safe-cardinality policy without history |
| `adaptive_greedy` | Allocation ablation that reproduces the supplied greedy batch |
| `adaptive_always_max` | Removes the safety guard and always uses maximum cardinality |

The supplied `greedy`, `no_asks` and `random` modes remain available as official
baselines.

## Runtime and packaging

The policy uses the Python standard library. It is deterministic, has no network
dependency and keeps only a small JSON memory object.

At 200 members, graph construction checks at most 19,900 pairs. The blossom
solver is cubic in the number of graph vertices, which remains within the
competition's per-call limit in the tested episodes.

The real subprocess benchmark on public seed 101 made 120 policy calls. Mean
latency was 0.136 seconds, p95 was 0.166 seconds and the maximum was 0.183
seconds against the 10-second limit. The largest request was 474,833 bytes and
the largest response was 911 bytes against the 1 MiB limits.

The guarded-history Docker image was run through the official isolated evaluator
on public seed 101, development variant. The episode was valid and eligible,
scored 0.5, reached 0.465 coverage and produced 10.0 mutual acceptances per 100.
Those metrics match the trusted local run. The image was 45,191,941 bytes,
well below the 2 GiB limit. The local proof is
`results/container_check_history.json`.

## Known risks

- More pairs do not guarantee more MSMI outcomes in a small stochastic episode.
- Member history is sparse and noisy, especially shortly after day 20.
- The history improvement is not statistically clear on the untouched holdout.
- Equal soft-field counts favor pairs with more observed answers.
- Clarification selects the first eligible records in state order.
- The history signal estimates each person's general behavior, not their
  response to one particular partner.
- Cold-start and sparse pools can still have very few feasible edges.
- The local quality refinement does not prove maximum weight among all maximum-
  cardinality matchings.
- Hidden evaluation worlds may differ from the public simulator.
