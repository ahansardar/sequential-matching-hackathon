# LuminaX Round 1 corrected evidence addendum

**Team:** LuminaX
**Members:** Ahan Sardar and Enakshee Mondal
**Date:** 10 October 2026

## Purpose

This short addendum answers the Round 1 feedback with new analysis. It does not
claim that a public result guarantees a private score or selection. Where the
new evidence weakens our original submission, we say so and change the
conclusion.

## What changed

| Question from the feedback | Correction | Decision |
|---|---|---|
| Were correlated scenario variants treated as independent? | All intervals now resample an entire generated seed, keeping its six variants together and giving each variant equal weight. | The reported history gain remains uncertain. |
| What do the two directional scores mean? | We define two event probabilities: whether `user_a` and whether `user_b` records Yes by the seven-day response deadline. We fit, calibrate and test them on three disjoint seed blocks. | This is a diagnostic estimator, not the matching score. |
| Are people with sparse profiles served differently? | We report coverage, unserved rate, waits and outcomes in four completeness bands. We also separate arrival timing and observable partner opportunity, then hide 50% and 100% of observed soft fields in controlled paired runs. | A large descriptive service gap exists. The masking tests and service strata test which explanations the evidence can support. |
| Does guarded cardinality improve completed outcomes? | We isolate the allocator with and without the history signal, then measure MSMI, mutual acceptances, dates, coverage, unserved members and waits. | We retain it only if the completed-outcome evidence supports it. |
| Is state-order clarification justified? | We compare graph-aware ordering and a stable arrival-day plus opaque-ID order against the old input-order rule. We also permute every observable list and constraint array. | The submitted rule no longer depends on arbitrary JSON member order. Its score effect is reported as uncertain. |

## Analysis rules

- The primary measure is mutual second-meeting intentions (MSMI) per 100
  arrived members. It is a rate, not a probability bounded by 1.
- Each comparison uses identical generated seeds and scenario variants for both
  methods.
- The six public variants are `development`, `sparse`, `cold_start`, `delayed`,
  `shift` and `drift`. Each receives equal weight.
- A bootstrap draw samples whole seed groups. It never separates variants that
  share a generated world.
- New component studies use separate seed blocks. The two masking conditions
  intentionally reuse the same profile-study worlds so their differences are
  paired.
- Policy features come only from the observable request. Member IDs, hidden
  simulator preferences, private seeds and future feedback are never features.
- A 95% interval that includes zero is reported as uncertain.

## 1. History signal with seed-grouped uncertainty

We reanalysed the saved 20-seed, six-variant comparison. The day-20 history
method scored **0.0208 MSMI per 100 higher** than the no-history method across
120 paired episodes. The corrected seed-grouped 95% interval is **-0.0375 to
0.0792**. The interval includes zero.

The variant mean differences were 0.0500 in development, 0.0500 in drift,
0.0250 in shift and 0 in cold-start, delayed and sparse. None was negative in
this block, but the overall gain is not established. We therefore retract any
wording that treats history as a proven improvement.

Evidence: [`results/corrected_history_seed_grouped.json`](results/corrected_history_seed_grouped.json)

## 2. Directional probability definitions and calibration

The old report described directional scores too loosely. The corrected targets
are:

- `user_a_recorded_yes_by_response_deadline`: the canonical `user_a` endpoint
  of an assigned introduction records Yes no later than its seven-day deadline.
- `user_b_recorded_yes_by_response_deadline`: the same event for the canonical
  `user_b` endpoint.

`user_a` and `user_b` are only canonical pair positions. The same estimator is
applied after swapping actor and candidate. A missing response at the deadline
is target 0 because the defined Yes-by-deadline event did not happen; it is not
interpreted as dislike.

Features are frozen immediately before assignment. Every assignment receives
40 follow-up days, so the holdout contains no right-censored response windows.
The model is fit on seeds 6001–6010, calibrated on 6031–6040 and evaluated once
on 6101–6110. Each block contains all six variants.

The fresh audit runs the actual submitted `adaptive_greedy` mode. The untouched
holdout contains 9,588 directional examples and 3,298 positives. Headline
calibration metrics give each scenario variant equal weight; the AUC uses all
holdout examples because it is a ranking statistic rather than a scenario
mean.

| Holdout estimator | Observed Yes | Mean prediction | Brier score | Equal-count ECE | AUC |
|---|---:|---:|---:|---:|---:|
| Logistic model before Platt calibration | 34.36% | 36.24% | 0.22330 | 0.03391 | 0.5638 |
| After disjoint Platt calibration | 34.36% | 36.28% | 0.22375 | 0.04010 | 0.5638 |
| Constant training-prevalence baseline | 34.36% | 36.20% | 0.22587 | 0.03578 | 0.5000 |

The post-calibration equal-variant Brier score has a seed-grouped 95% interval
of **0.21960 to 0.22900**. Calibration-in-the-large is **+0.0192**, with an
interval of **+0.0022 to +0.0328**. The model overpredicts Yes on this holdout.
Its paired Brier improvement over the constant baseline is **-0.00212**, with a
seed-grouped interval of **-0.00275 to -0.00147**. Platt calibration changes
Brier by **+0.00045** versus the raw model, with an interval of **-0.00017 to
+0.00105**. The extra calibration step is therefore not supported.

Calibration also differs by profile information available at assignment:

| Observed soft fields | Examples | Observed Yes | Mean prediction | Brier | Equal-count ECE |
|---:|---:|---:|---:|---:|---:|
| 0 | 2,188 | 32.91% | 34.92% | 0.22095 | 0.04241 |
| 1-2 | 2,300 | 35.04% | 35.47% | 0.22696 | 0.04208 |
| 3-6 | 131 | 35.88% | 35.13% | 0.22690 | 0.14416 |
| 7 | 4,969 | 34.72% | 37.35% | 0.22336 | 0.05357 |

The 3-6 group is too small for a stable bin estimate. Complete profiles are
overpredicted by 2.63 percentage points. Shift and drift also overpredict by
3.16 and 3.00 points. These subgroup checks are diagnostic point estimates,
not independent causal comparisons.

The fitted model shows weak discrimination and a small, repeatable Brier
improvement over the constant baseline. Its calibration-in-the-large remains
wrong in the positive direction, subgroup calibration is uneven, and Platt
calibration does not improve the raw model. We therefore do not treat this
estimator as ready for policy scoring. The result directly supports the
feedback that directional calibration still needs development.

These probabilities are not the policy's compatibility score. They are kept
outside the runtime unless they beat the constant training-prevalence baseline
and remain calibrated on new seed groups.

Evidence: [`results/corrected_directional_calibration.json`](results/corrected_directional_calibration.json)

## 3. Service by profile completeness

Completeness is the number of the seven soft fields observed when a member first
appears. The cohort is measured before masking and never changes later. The
unmasked study contains 10 seed groups × 6 variants = 60 episodes. The 12,000
member observations below are correlated across variants, so they are useful
descriptive totals, not 12,000 independent worlds.

| Observed soft fields | Member observations | Coverage | Unserved | Median wait if served | 90th-percentile wait | MSMI member rate |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | 3,975 | 23.80% | 76.20% | 8.0 days | 18.0 days | 0.33% |
| 1–2 | 4,001 | 23.02% | 76.98% | 7.0 days | 17.0 days | 0.42% |
| 3–6 | 259 | 26.25% | 73.75% | 8.0 days | 18.0 days | 0.39% |
| 7 | 3,765 | 50.52% | 49.48% | 0.0 days | 13.0 days | 1.35% |

Fully complete profiles receive much faster and more frequent service. The
3–6-field band is small, so its outcome rate is especially noisy. Conditioning
only on having at least one partner not ruled out at first appearance leaves
coverage at 23.83%, 23.03%, 26.25% and 59.99% across the same four bands. This
does not remove the gap.

That opportunity measure is deliberately observable and conservative. Missing
hard fields leave many partners "not ruled out" even though they may later fail
a constraint. The mean count of immediately decidable feasible partners is
zero in the first three soft-completeness bands and 0.41 in the complete band.
This shows that soft completeness is strongly tied to hard-information
readiness in the generator. The saved output therefore includes cells crossing
soft completeness, arrival day and observable partner opportunity instead of
claiming that soft answers alone caused the service difference.

In the paired 50% masking condition, MSMI changed by **+0.0583** with a
seed-grouped 95% interval of **-0.0583 to 0.1750**. Coverage changed by
**-0.017 percentage points** with an interval of **-0.167 to 0.117 percentage
points**. The coverage gap changed by **-0.19 percentage points**, with an
interval of **-0.73 to +0.27 percentage points**. This intervention did not
meaningfully reduce the service gap.

When all observed soft fields are hidden from the policy, MSMI changes by
**-0.0083**, with a seed-grouped 95% interval of **-0.1500 to 0.1250**.
Coverage changes by **-0.117 percentage points**, with an interval of **-0.292
to +0.050 percentage points**. The largest-minus-smallest cohort coverage gap
falls by only **0.28 percentage points**, with an interval from a **0.74-point
reduction to a 0.14-point increase**. Even removing every soft field does not
remove the large service gap.

The safe conclusion is descriptive: service differs sharply with starting
profile completeness, while these masking interventions do not by themselves
prove that the soft fields cause the gap. Arrival order, availability, hard
constraints and the simulator's generated population can also contribute.

Evidence:
[`results/corrected_profile_completeness.json`](results/corrected_profile_completeness.json) and
[`results/corrected_profile_completeness_all_masked.json`](results/corrected_profile_completeness_all_masked.json)

## 4. Guarded cardinality and completed outcomes

We first kept the current history score fixed and changed only allocation:
greedy versus guarded global allocation. Across 10 fresh seed groups and all six
variants, guarded allocation changed MSMI by **-0.0750** with a seed-grouped 95%
interval of **-0.2000 to 0.0333**. It shortened median first-service wait by
**0.36 days**, with an interval of **0.09 to 0.68 days shorter**, but did not
establish an MSMI improvement.

We then removed the uncertain history signal and compared compatibility-greedy
allocation with guarded cardinality. Both score **0.2750 MSMI per 100**; the
paired difference is **0.0000**, with a seed-grouped 95% interval of **-0.0333
to 0.0333**. Guarded cardinality has slightly lower coverage, **0.32825 versus
0.32867**, and lower mutual acceptances per 100, **5.20 versus 5.30**. It
shortens median first-service wait by **0.175 days**, with an interval of
**0.042 to 0.325 days shorter**. Under the published ranking order, the tied
primary score moves to coverage, so greedy wins this comparison.

The allocator may improve a service measure without improving completed
outcomes. We therefore do not use introductions created, internal edge score or
runtime as evidence of relationship success.

Evidence:
[`results/corrected_allocation_outcomes.json`](results/corrected_allocation_outcomes.json) and
[`results/corrected_safe_cardinality_no_history.json`](results/corrected_safe_cardinality_no_history.json)

## 5. Clarification order

The earlier research policy asked for incomplete hard constraints in observable
state order. That is reproducible but brittle: a semantically identical JSON
request could change who received a question.

We first compared the old rule with a graph-aware challenger that asks about a
member with more currently known, potentially feasible partners. It uses only
the public state. Equal priorities retain state order.

Across 10 fresh seed groups and six variants, graph-aware order changed MSMI by
**-0.0417**, with a seed-grouped 95% interval of **-0.1833 to 0.0833**. It
shortened median first-service wait by **1.58 days** (95% interval **0.93 to
2.28 days shorter**) and the 90th percentile by **0.99 days** (95% interval
**0.43 to 1.59 days shorter**). Ask cost was unchanged.

The MSMI evidence did not justify the graph-aware score change. The waiting-
time improvement remains a service trade-off, not a win on the competition
objective.

The submitted mode now uses a narrower correction. It orders eligible asks by
arrival day and then opaque member ID. IDs are only a deterministic tie-break;
they are not model features. Against the old input-order rule on 20 fresh seed
groups and all six variants, the stable rule changed MSMI by **+0.0208 per
100**, with a seed-grouped 95% interval of **-0.0958 to 0.1417**. Coverage
changed by **+0.054 percentage points**, with an interval of **-0.100 to
+0.221 points**. Ask cost was identical. These score effects are uncertain.

The correctness result is stronger: the submitted action stayed identical
across 120 order-only permutations covering members, introductions, feedback,
ask logs and constraint arrays. We adopt the stable rule as an order-invariance
fix, not as a claimed MSMI improvement.

Evidence: [`results/corrected_clarification_order.json`](results/corrected_clarification_order.json),
[`results/corrected_member_order.json`](results/corrected_member_order.json) and
[`results/edge_case_audit.json`](results/edge_case_audit.json)

## 6. Edge cases and safeguards

| Risk | Safeguard or test |
|---|---|
| Two variants share one generated world | Bootstrap samples all variants for that seed together. |
| A seed/variant episode is duplicated or missing | The validator rejects duplicate and incomplete rectangular blocks. |
| Fit data leaks into calibration or holdout | The three seed sets must be disjoint; validation fails on overlap. |
| A response window has not matured | All assignments receive 40 follow-up days; any right-censored item is rejected. |
| No response is mistaken for dislike | The target is explicitly Yes-by-deadline, not latent preference. |
| A sparse cohort has zero members or zero served members | Rates use safe denominators; wait statistics are omitted when nobody is served. |
| Missing soft fields create accidental score credit | Missing values add no compatibility points. |
| A hard constraint is missing or declined | The pair is not declared feasible; clarification never overrides feasibility. |
| No feasible pairs exist | The policy returns an empty pair list. |
| Ask budget is below one constraints question | The policy submits no ask. |
| Member, feedback or constraint-array order changes | The submitted action remains identical; 120 order-only permutations pass. |
| Scores tie | Canonical pair IDs resolve the tie; IDs never enter the score. |
| The graph is fully connected | A 200-member dense graph returns 100 non-overlapping pairs in 0.12 seconds in the direct audit. |
| Feedback is duplicated or has impossible timing | Evidence parsing rejects duplicates and enforces lower and upper time bounds. |
| Memory comes from an older policy shape | Scalar, list and stale mapping inputs are replaced or safely updated. |
| Delayed, sparse, shifted, drifting or cold-start conditions | Every study includes all six variants and reports their equal-weight mean. |
| A complex component improves an internal proxy only | Promotion is based on completed MSMI first, followed by the published tie-break order. |
| JSON contains invalid numbers | Saved artifacts use strict JSON; the validator rejects NaN and infinity. |
| Public code accidentally depends on hidden truth | Policy code receives only the documented observable request and runs offline. |

The fuller runtime, timing, service and evidence matrix is in
[`docs/EDGE_CASE_REGISTER.md`](docs/EDGE_CASE_REGISTER.md).

## 7. Revised policy claim

The corrected container default is the stable-clarification compatibility-
greedy method. We
remove both the uncertain history signal and guarded cardinality from the
selected runtime. They remain named research ablations so every result can be
reproduced. This is a correction to our original selection, not a claim that
greedy is universally optimal.

What remains defensible is the boundary of the method:

1. clarify only missing reciprocal hard constraints within budget, using a
   stable arrival-day and opaque-ID order;
2. reject every pair that is not reciprocally feasible;
3. rank feasible unseen pairs with transparent observed compatibility;
4. allocate deterministically;
5. use delayed feedback only after it has matured and only if fresh evidence
   supports the component;
6. return valid empty output when no safe action exists.

## Reproduction and independent checks

```text
python experiments/confidence_audit.py --incumbent adaptive_legacy --challenger adaptive --seeds 4001-4020 --variants all --workers 4 --resamples 20000 --output results/corrected_history_seed_grouped.json
python experiments/component_audit.py --incumbent adaptive_history_greedy --challenger adaptive --seeds 6301-6310 --variants all --workers 4 --resamples 20000 --output results/corrected_allocation_outcomes.json
python experiments/component_audit.py --incumbent adaptive --challenger adaptive_graph_asks --seeds 6401-6410 --variants all --workers 4 --resamples 20000 --output results/corrected_clarification_order.json
python experiments/component_audit.py --incumbent adaptive_greedy --challenger adaptive_legacy --seeds 6501-6510 --variants all --workers 2 --resamples 20000 --output results/corrected_safe_cardinality_no_history.json
python experiments/component_audit.py --incumbent adaptive_input_order_greedy --challenger adaptive_greedy --seeds 7201-7220 --variants all --workers 4 --resamples 10000 --output results/corrected_member_order.json
python experiments/profile_completeness_audit.py --seeds 6201-6210 --variants all --mask-rate 0.5 --workers 4 --resamples 20000 --output results/corrected_profile_completeness.json
python experiments/profile_completeness_audit.py --seeds 6201-6210 --variants all --mask-rate 1 --workers 4 --resamples 20000 --input-unmasked results/corrected_profile_completeness.json --output results/corrected_profile_completeness_all_masked.json
python experiments/directional_calibration.py --training-seeds 6001-6010 --calibration-seeds 6031-6040 --holdout-seeds 6101-6110 --variants all --workers 4 --resamples 5000 --output results/corrected_directional_calibration.json
python experiments/edge_case_audit.py --output results/edge_case_audit.json
python experiments/validate_corrected_addendum.py
```

The final validator reloads saved JSON, rejects non-finite values, verifies
complete seed-by-variant blocks, checks split separation and recomputes every
paired mean directly from the raw episode rows. It does not call the analysis
helper that produced the results.

## Limitations

- All evidence comes from the published synthetic simulator. It may not
  transfer to real matching outcomes.
- The new component studies contain 10 independent seed groups each. Rare MSMI
  outcomes still create wide intervals.
- The profile cohorts are observational. Controlled masking removes observable
  soft information but does not change correlated arrival, availability or
  hard-constraint patterns.
- The not-ruled-out partner count is an observable opportunity proxy. Missing
  hard constraints can make it larger than the final feasible partner count.
- Calibration is evaluated on an untouched public-simulator holdout, not on
  real user probabilities.
- The calibration sample contains assigned introductions under one policy. It
  does not establish probability quality for every unassigned feasible pair.
- Several questions were tested. We show negative results and do not select a
  method only because one public block looks favourable.

## Request for reconsideration

This addendum implements the requested corrections and makes the weaker
findings explicit. We respectfully ask that LuminaX be reconsidered using this
corrected evidence package. We understand that reconsideration does not
guarantee selection.
