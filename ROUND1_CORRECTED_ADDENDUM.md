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
| Are people with sparse profiles served differently? | We report coverage, unserved rate, waits and outcomes in four completeness bands. We also hide 50% and 100% of observed soft fields in controlled paired runs. | A large descriptive service gap exists. The masking tests show whether observed soft information causes it. |
| Does guarded cardinality improve completed outcomes? | We isolate the allocator with and without the history signal, then measure MSMI, mutual acceptances, dates, coverage, unserved members and waits. | We retain it only if the completed-outcome evidence supports it. |
| Is state-order clarification justified? | We compare it with a public-observation graph-aware order on a fresh matched seed block. | Graph-aware ordering reduces waiting but does not improve MSMI; state order remains the primary-score choice. |

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

The untouched holdout contains 9,486 directional examples and 3,390 positives.

| Holdout estimator | Observed Yes | Mean prediction | Brier score | ECE | AUC |
|---|---:|---:|---:|---:|---:|
| Logistic model before Platt calibration | 35.74% | 36.11% | 0.22746 | 0.00701 | 0.5574 |
| After disjoint Platt calibration | 35.74% | 36.44% | 0.22780 | 0.01207 | 0.5574 |
| Constant training-prevalence baseline | 35.74% | 36.01% | 0.22966 | 0.00272 | 0.5000 |

The post-calibration Brier score has a seed-grouped 95% interval of **0.22478
to 0.23115**. Calibration-in-the-large is **+0.0070**, with an interval of
**-0.0070 to 0.0197**. The two canonical directions have observed rates of
36.07% and 35.40%, mean predictions of 36.47% and 36.41%, and Brier scores of
0.22873 and 0.22686.

The fitted model shows weak discrimination and only a small Brier improvement
over the constant baseline. Platt calibration makes both Brier score and ECE
worse on the untouched holdout than the uncalibrated model. Shift has the
largest variant-level mean overprediction, 2.05 percentage points. We therefore
do not treat this estimator as ready for policy scoring. The result directly
supports the feedback that directional calibration still needs development.

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
| 0 | 3,975 | 23.82% | 76.18% | 8.0 days | 20.0 days | 0.48% |
| 1–2 | 4,001 | 23.02% | 76.98% | 8.0 days | 17.0 days | 0.22% |
| 3–6 | 259 | 25.48% | 74.52% | 7.5 days | 24.0 days | 0.77% |
| 7 | 3,765 | 50.89% | 49.11% | 0.0 days | 12.0 days | 1.06% |

Fully complete profiles receive much faster and more frequent service. The
3–6-field band is small, so its outcome rate is especially noisy.

In the paired 50% masking condition, MSMI changed by **-0.0250** with a
seed-grouped 95% interval of **-0.1167 to 0.0500**. Coverage changed by
**-0.05 percentage points** with an interval of **-0.13 to 0.03 percentage
points**. The coverage gap changed by **-0.02 percentage points**, with an
interval of **-0.15 to 0.15 percentage points**. This intervention did not
meaningfully reduce the service gap.

When all observed soft fields are hidden from the policy, MSMI again changes by
**-0.0250**, with a seed-grouped 95% interval of **-0.1083 to 0.0417**.
Coverage changes by **-0.05 percentage points**, with an interval of **-0.16 to
0.05 percentage points**. The largest-minus-smallest cohort coverage gap falls
by only **0.21 percentage points**, with an interval from a **0.55-point
reduction to a 0.09-point increase**. Even removing every soft field does not
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

The incumbent asks for incomplete hard constraints in observable state order.
The challenger asks first about a member with more currently known, potentially
feasible partners. It uses only the public state. Equal priorities retain state
order.

Across 10 fresh seed groups and six variants, graph-aware order changed MSMI by
**-0.0417**, with a seed-grouped 95% interval of **-0.1833 to 0.0833**. It
shortened median first-service wait by **1.58 days** (95% interval **0.93 to
2.28 days shorter**) and the 90th percentile by **0.99 days** (95% interval
**0.43 to 1.59 days shorter**). Ask cost was unchanged.

The MSMI evidence does not justify replacing state order in a primary-score
submission. The waiting-time improvement is real enough to record as a service
trade-off, not as a win on the competition objective.

Evidence: [`results/corrected_clarification_order.json`](results/corrected_clarification_order.json)

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
| Scores tie | Deterministic observable order resolves the tie. |
| Delayed, sparse, shifted, drifting or cold-start conditions | Every study includes all six variants and reports their equal-weight mean. |
| A complex component improves an internal proxy only | Promotion is based on completed MSMI first, followed by the published tie-break order. |
| JSON contains invalid numbers | Saved artifacts use strict JSON; the validator rejects NaN and infinity. |
| Public code accidentally depends on hidden truth | Policy code receives only the documented observable request and runs offline. |

## 7. Revised policy claim

The corrected container default is the simple compatibility-greedy method. We
remove both the uncertain history signal and guarded cardinality from the
selected runtime. They remain named research ablations so every result can be
reproduced. This is a correction to our original selection, not a claim that
greedy is universally optimal.

What remains defensible is the boundary of the method:

1. clarify only missing reciprocal hard constraints within budget;
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
python experiments/profile_completeness_audit.py --seeds 6201-6210 --variants all --mask-rate 0.5 --workers 4 --resamples 20000 --output results/corrected_profile_completeness.json
python experiments/profile_completeness_audit.py --seeds 6201-6210 --variants all --mask-rate 1 --workers 4 --resamples 20000 --input-unmasked results/corrected_profile_completeness.json --output results/corrected_profile_completeness_all_masked.json
python experiments/directional_calibration.py --training-seeds 6001-6010 --calibration-seeds 6031-6040 --holdout-seeds 6101-6110 --variants all --workers 4 --resamples 5000 --output results/corrected_directional_calibration.json
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
