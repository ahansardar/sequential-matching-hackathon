# Safe-cardinality matching policy

Status: current competition policy.

This policy makes one careful change to the strongest supplied baseline. It
tries to serve more people in each daily batch, but accepts the change only when
the total observed compatibility does not decrease.

It uses no external model, API, network connection or hidden simulator value.

## Daily flow

Each day has two phases.

1. Ask up to four available people for their missing hard-constraint bundle.
2. Build the reciprocal feasible graph after the answers arrive.
3. Give each feasible pair an observed compatibility score.
4. Build both a greedy batch and a maximum-cardinality batch.
5. Use the maximum-cardinality batch only if it is strictly larger and its total
   compatibility is at least as high as the greedy batch.

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

This is the same transparent score used by the supplied greedy baseline. Keeping
the score fixed isolates the effect of allocation and reduces public-simulator
overfitting.

## Allocation

The greedy batch takes the highest-scoring remaining edge until no additional
non-overlapping edge can be added.

The alternative batch uses Edmonds' blossom algorithm to find a maximum-
cardinality matching in the general graph. A deterministic local improvement
then raises observed compatibility without reducing the number of pairs.

The policy accepts the alternative only when both statements are true:

```text
alternative pair count > greedy pair count
alternative total compatibility >= greedy total compatibility
```

This guard prevents the global allocator from changing a batch merely because a
different maximum matching exists.

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
and feedback-based tie-breaks. Some won small development screens, but none
improved the last untouched holdout. The feedback tie-break's 300-episode paired
estimate was 0.0133 points above safe-cardinality, but its 95% normal interval
ranged from -0.0200 to 0.0467 and it lost the final 120-episode holdout. We kept
the simpler policy instead of tuning to favorable public or development seeds.
The machine-readable selection summary is
`results/algorithm_selection_summary.json`.

These are synthetic simulator results. They do not guarantee a private-evaluation
win or describe real relationship outcomes.

## Experiment modes

| Mode | Purpose |
|---|---|
| `adaptive` | Current guarded safe-cardinality policy |
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

The final Docker image was also run through the official isolated evaluator on
public seed 101, development variant. The episode was valid and eligible, the
container action trace exactly matched the local action trace, and the image was
43.1 MiB against the 2 GiB limit. The recorded proof is
`results/adaptive_container_seed101_development.json`.

## Known risks

- More pairs do not guarantee more MSMI outcomes in a small stochastic episode.
- The compatibility score uses equality and does not estimate directional
  acceptance probabilities.
- Cold-start and sparse pools can still have very few feasible edges.
- The local quality refinement does not prove maximum weight among all maximum-
  cardinality matchings.
- Hidden evaluation worlds may differ from the public simulator.
