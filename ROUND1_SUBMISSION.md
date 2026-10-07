# Round 1 research submission

## Team details

- **Team name:** LuminaX
- **Team members:** Ahan Sardar and Enakshee Mondal
- **Repository:** `https://github.com/ahansardar/sequential-matching-hackathon`
- **Selected policy:** Guarded-history safe-cardinality
- **Policy version:** `guarded-history-2.1`
- **Prepared on:** 8 October 2026

## Summary

We treat the task as a sequential graph-matching problem. The policy must make
reciprocal introductions while information is incomplete and outcomes arrive
later. A strong pair score is not enough because choosing one pair changes the
options available to everybody else.

Our selected method has four parts:

1. Ask for missing hard constraints within the daily budget.
2. Remove every pair that is not reciprocally feasible.
3. Rank feasible pairs by observed compatibility and mature response history.
4. Use global graph matching only when it serves more people without lowering
   the total policy score.

The policy is deterministic, offline, and written with the Python standard
library. It does not use hidden simulator values, member IDs as predictors,
future feedback, private seeds, an external API, or a network connection.

## How we understand the problem

The primary score is Mutual Second-Meeting Intention, or MSMI, per 100 arrived
members. A pair succeeds only when all of these events happen:

1. Both people respond to the introduction.
2. Both people answer Yes.
3. A date happens within 30 days of assignment.
4. Both people request a second meeting within three days of the date.

One successful pair among 200 arrived members scores 0.5. The final outcome is
rare, so one extra successful pair can move a small experiment sharply.

The policy must also manage the whole pool. A locally strong pair can block two
other strong pairs. Waiting may preserve a future option, but waiting can also
leave people unserved. Clarification can unlock a valid edge, but the daily ask
budget is limited.

## Hypothesis

Our final hypothesis is:

> A constraint-first policy that combines compatibility, mature observed
> response history, and guarded maximum-cardinality allocation may improve
> MSMI over a purely greedy policy without risking reciprocal feasibility.

The hypothesis has three testable claims:

- Hard constraints must remain separate from scoring.
- History should affect decisions only after enough time has passed for
  feedback to arrive.
- Global allocation should replace greedy allocation only when it adds pairs
  without lowering the batch's total policy score.

## Observable information

The policy uses only the current request:

- arrived members and their availability;
- observed questionnaire fields and field status;
- earlier introductions;
- feedback whose observation day has arrived;
- the current day and remaining ask budget; and
- the policy's small JSON memory object.

The policy never reads member truth, response propensity, private coefficients,
the world seed, future arrivals, or future outcomes.

## Reciprocal constraints

We create an edge between two members only when the official `eligibility`
function returns `feasible`.

The check covers both people's requirements:

- acceptable age range;
- stated genders to meet;
- relationship structure;
- smoking constraints;
- children-related constraints;
- acceptable zones; and
- overlapping schedules.

We also remove unavailable members, repeated pairs, members with unresolved
hard constraints, and overlapping assignments. Soft compatibility never
overrides a hard failure.

## Clarification policy

The daily ask budget is 12. A hard-constraint bundle costs 3, so the policy can
ask at most four members per day.

The policy asks available members who have unanswered hard constraints and no
declined hard field. It does not ask again after a declined hard field because
the field will remain unknown.

The current implementation takes the first eligible members in the observable
state order. It does not rank them by graph degree or expected edge unlocks.
This deterministic rule can spend budget on a member who has few plausible
partners, so clarification remains a known weakness.

We tested an expected-unlock policy that asked members whose answers could open
the most plausible reciprocal edges. It scored 0.3833 versus 0.2500 on its
30-episode screen. On a fresh 60-episode block, it scored 0.2583 versus 0.3083.
The gain did not repeat, so we kept the simpler clarification policy.

## Pair score

For each feasible pair, we count equal observed values across seven soft fields:

- relationship goal;
- relationship pace;
- lifestyle;
- conversation preference;
- emotional availability;
- space for a relationship; and
- relocation preference.

A missing value gives no point. It is not treated as agreement or disagreement.
This raw count favors pairs with more mutually observed fields. In the public
day-30 snapshots, only 36% to 46% of soft fields are observed across the ten
pools. We therefore treat the score as a conservative ranking rule, not a
calibrated compatibility probability.

The seven fields have equal weight. This is a transparency choice, not a claim
that every field has the same relationship with MSMI. Weighted, goal-only and
learned alternatives failed to produce a repeatable holdout gain.

Before day 20, the pair score is:

```text
pair score = 100 * observed compatibility count
```

From day 20, the policy adds a small history term for both members:

```text
pair score = 100 * observed compatibility count
           + history quality of member A
           + history quality of member B
```

History quality contains two Bayesian-smoothed estimates:

- the member's observed response rate; and
- the member's Yes rate among recorded responses.

The response prior is 0.765 and the acceptance prior is 0.46. Development
rollouts produced rates close to these values. The later fixed training asset,
which contains 18,149 introductions from 240 episodes, records rates of 0.7592
and 0.4574. We chose prior strength four as a small-sample regularizer. It was
not fitted by the final outcome model.

The policy adds the log-odds of the two estimates. It clips each member's
history contribution to the range -20 to 20. A pair's history term is therefore
between -40 and 40. One compatibility point is worth 100, so history cannot
override a full compatibility-point difference on one edge.

The factor of 100 keeps observed compatibility dominant on an individual edge.
History normally breaks close choices instead of overriding a full
compatibility point.

## Daily allocation

The policy builds two batches.

The first batch uses greedy allocation. It selects the highest-scoring unused
edge, marks both members as used, and continues through the sorted edge list.

The second batch uses Edmonds' blossom algorithm to find a maximum-cardinality
matching in the general graph. A deterministic local improvement step then
raises the policy score without reducing the number of pairs.

The policy selects the global batch only when both conditions are true:

```text
global pair count > greedy pair count
global total policy score >= greedy total policy score
```

If either condition fails, the policy returns the greedy batch.

We measured this branch on seeds 5301-5303 across all six scenario families.
The global batch ran on 26 of 1,080 decision days. It ran on 4.45% of the 584
days that had at least one feasible edge. The branch is active but uncommon. It
did not run in the sparse scenario during this telemetry block.

## Missing and delayed information

The policy follows these rules:

- A missing hard field blocks the pair until clarification resolves it.
- A declined field remains missing and is not asked again.
- A missing soft field adds no compatibility point.
- Feedback affects the score only after its `observed_day` arrives.
- A missing introduction response counts as a response trial, but not as a
  response or rejection.
- Acceptance history counts only recorded Yes or No responses.
- Recent unresolved introductions are not labelled as failed outcomes.
- Independent episodes start with empty policy memory.

These rules prevent future information and right-censored outcomes from leaking
into earlier decisions.

## Baselines and ablations

We compare against the three official baselines on identical seeds:

- `greedy`, which asks for hard constraints and greedily matches by soft-field
  equality;
- `no_asks`, which never clarifies missing information; and
- `random`, which selects random feasible pairs.

The selected policy also exposes focused ablations:

| Mode | Removed or changed component |
|---|---|
| `adaptive_legacy` | Removes the day-20 history term |
| `adaptive_greedy` | Removes global allocation |
| `adaptive_always_max` | Removes the allocation safety guard |

The one-seed starter reference is a smoke test, not strong evidence:

| Method | Public primary score | Coverage | Mutual acceptances per 100 |
|---|---:|---:|---:|
| Greedy | 0.500 | 0.408 | 7.583 |
| No asks | 0.333 | 0.174 | 2.833 |
| Random feasible | 0.250 | 0.412 | 6.667 |

## Completed experiments

Every comparison below used matched seeds and all six scenario families.

### Guarded maximum-cardinality allocation

The earlier safe-cardinality policy tied greedy at 0.3889 on the 18 public
episodes and increased mutual acceptances from 5.50 to 5.64 per 100. On seeds
1101-1110, it scored 0.542 versus 0.525 for greedy.

### Day-20 history gate

| Evaluation block | Episodes per policy | Guarded history | Previous policy |
|---|---:|---:|---:|
| Seeds 3901-3910 | 60 | 0.5000 | 0.4750 |
| Fresh seeds 4001-4020 | 120 | 0.2708 | 0.2500 |
| Public seeds 101-103 | 18 | 0.3611 | 0.3889 |

The larger independent blocks favored guarded history, but the small public
block favored the previous method. We therefore treat the gain as uncertain,
not guaranteed.

A 20,000-resample paired bootstrap on the 120-episode holdout estimated a 95%
interval from -0.0167 to 0.0583 for the score difference. The interval includes
zero. The holdout contains five more MSMI outcomes for guarded history, but it
does not establish a statistically clear improvement. We retain guarded history
as the score-seeking default because its point estimate improved and no scenario
family mean fell on this holdout. `adaptive_legacy` remains the conservative
alternative.

### Rejected pair-specific methods

We trained direct and decomposed outcome models on 18,149 introductions from
240 declared synthetic episodes. The strongest history model won its tuning
screen but lost its untouched holdout by 0.0917 MSMI per 100. A static model
won one holdout and lost the next.

We then tested a stricter pair-specific scorer that could not reduce pair count
or raw compatibility. Its best conservative formula scored 0.3250 versus
0.3083 on a 60-episode confirmation, then lost the 120-episode final holdout by
0.3792 to 0.4208. We rejected it.

Other rejected ideas include goal-only scoring, waiting thresholds, extra soft
questions, sparse-zone asks, early feedback, exact maximum-weight experiments,
and explore-first bandit policies. Small development wins did not survive fresh
seed blocks.

We also tested partial credit for missing soft fields. Credit 0.25 scored 0.5333
versus 0.5000 on a 30-episode screen. It then lost 0.4500 versus 0.5000 on a
fresh 60-episode confirmation. Credit 0.50 lost the first screen. We kept both
variants out of the submission policy.

## Selection rule

We select a competition default only when it:

1. Beats the incumbent on a matched development screen.
2. Repeats the gain on a fresh untouched block.
3. Preserves episode validity and reciprocal constraints.
4. Remains deterministic, offline, and within the published limits.

We also report a paired 95% confidence interval. An interval above zero supports
a strong improvement claim. An interval that includes zero means the measured
gain remains uncertain, even when the point estimate wins.

We do not select a method from one favorable seed. We record rejected methods
in `docs/DECISIONS.md` and keep them out of the submission runtime.

## Where the method may fail

- MSMI outcomes are rare, so the measured difference between two policies has
  high variance.
- General member history does not predict one specific pair reliably.
- The measured history gain has a paired 95% interval that includes zero.
- Equal soft-field counts favor pairs with more observed answers.
- Clarification follows state order rather than graph value.
- Sparse geography can leave very few feasible edges.
- Cold-start members have no behavior history.
- The local quality step does not prove a maximum-weight matching among all
  maximum-cardinality matchings.
- A hidden evaluation world may differ from the public simulator.
- More introductions can increase coverage without increasing MSMI.

The simulator contains invented people and invented outcomes. These scores do
not establish real relationship quality or justify use with real people.

## Reproducibility and execution

The selected runtime uses Python 3.10 or later and the standard library. It has
no external inference asset, API key, network dependency, GPU requirement, or
inference randomness.

Run the checks from the repository root:

```text
python -m unittest -v
python verify_data.py
docker build -t sequential-policy:submission .
python evaluate.py --image sequential-policy:submission --seeds 101 --variants development --output results/container_check.json
```

The current repository passes 61 tests. `verify_data.py` verifies all 2,000
profiles and 71 published files. The submission image passed the isolated
seed-101 development check and remained below the 2 GiB image limit.

## Round 1 conclusion

Our selected policy is intentionally conservative. It protects every hard
constraint, uses delayed feedback only after observation, and improves pool
allocation without trusting a complex score that failed holdout testing.

We do not claim a guaranteed winning score or a reliable score of 0.9. Our claim
is narrower: guarded history has the best selected point estimate, while its
advantage over the no-history ablation remains statistically uncertain.

## Final checklist

- [ ] Ask the teammate to check every score and limitation.
- [ ] Export a frozen PDF if the Google Form requests one.
- [ ] Submit through the official Google Form before 9 October 2026, 23:59 IST.
- [ ] Save the submission receipt and the exact submitted file.
