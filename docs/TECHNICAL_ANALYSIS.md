# Technical analysis and recommended direction

## What wins the challenge

The primary score is mean Mutual Second-Meeting Intention (MSMI) per 100 arrived
members, weighted equally across six scenario families. Coverage, mutual
acceptance, clarification cost and runtime matter only as ordered tie-breakers.
The policy therefore should optimise mature pair outcomes without producing an
invalid action; raw match volume is not the objective.

The evaluation is sequential. A policy acts for 60 days, receives delayed and
selective feedback, then receives 40 follow-up days with no new decisions. Each
person can have only one outstanding introduction, pairs cannot repeat and every
batch must be non-overlapping and reciprocally feasible.

## Baseline findings

The checked reference runs use seed 101 across all six public variants. They are
small demonstrations, not statistically stable estimates.

| Baseline | Primary score | Coverage | Mutual acceptances / 100 | Ask cost |
|---|---:|---:|---:|---:|
| Greedy | 0.500 | 0.408 | 7.583 | 205 |
| No asks | 0.333 | 0.174 | 2.833 | 0 |
| Random feasible | 0.250 | 0.412 | 6.667 | 205 |

Three useful signals emerge. Clarification materially expands the feasible
graph; random feasible matching gets similar coverage but weaker outcomes than
soft-similarity greedy matching; and sparse geography is the hardest public
scenario, where all checked baselines score zero MSMI on this single seed.

## Main weaknesses in the starter policy

1. **Clarification is first-come-first-served.** It asks the first four eligible
   people for the complete hard bundle, regardless of whether answers are likely
   to unlock a competitive edge.
2. **Pair value is crude.** It counts equal soft-field matches, ignores observed
   feedback and treats every field as equally useful in every scenario.
3. **Allocation is greedy.** Taking the highest edge first can reduce total batch
   value when two strong edges compete for the same member.
4. **No explicit waiting value exists.** The baseline matches whenever feasible,
   even when uncertainty or expected near-term supply makes waiting attractive.
5. **No learning occurs.** Memory is passed through unchanged and delayed
   feedback does not update estimates.
6. **No uncertainty-aware exploration occurs.** Selective outcomes can reinforce
   the policy's initial choices unless exploration is deliberate and constrained.

## Recommended Round 1 hypothesis

> A constraint-first policy combining value-of-information clarification,
> uncertainty-aware reciprocal pair value and improved batch allocation will
> increase MSMI over greedy matching, especially in cold-start and sparse-supply
> settings, without sacrificing episode validity.

This is testable with three components and clean ablations:

### 1. Constraint-first candidate graph

Build edges only after every known reciprocal hard rule passes. Classify blocked
edges by the smallest unresolved constraint set. Missing data must never be
imputed as permission. Track why each person is unserved for audit and analysis.

### 2. Targeted clarification

Estimate the value of an ask from how many promising blocked edges it could
unlock, the member's scarcity of alternatives, edge competition and the ask
cost. Prefer hard bundles for members near the allocation frontier. Use soft asks
only when the answer can plausibly reorder otherwise feasible edges.

An initial deterministic priority can be implemented without a trained model:

`ask_value = unlockable_edge_quality × scarcity × decision_relevance / cost`

The ablation is the same policy with the supplied first-come clarification rule,
and a second ablation disables asks entirely.

### 3. Reciprocal scoring and allocation

Keep directional scores distinct: expected A-to-B response and B-to-A response
are not interchangeable. Combine them into a declared pair objective without
claiming independence unless the model actually assumes it. Use observed soft
compatibility, feedback history, missingness indicators, response maturity and
uncertainty.

For allocation, compare starter greedy selection with an improved batch matcher.
A practical first implementation is sorted edges followed by deterministic
two-edge exchange improvements. It stays lightweight and can directly address
the counterexample in the problem statement. If an exact matching dependency is
introduced later, pin and license it and confirm cold startup under the 10-second
limit.

## Experiment design

- Develop on declared simulator seeds and the six training pools.
- Select method settings using `public_07` and `public_08` only.
- Reserve `public_09` and `public_10` for limited final development checks.
- Compare team policy, greedy, no-asks and random with identical seeds across all
  six variants.
- Report scenario means, uncertainty across seeds, coverage, assignments, mutual
  acceptances, dates, MSMI, ask cost, missing feedback, waiting time and runtime.
- Include component ablations: targeted asks off, allocation improvement off and
  learning/uncertainty term off if implemented.
- Audit invalid/empty episodes separately; a single invalid assessed episode
  disqualifies technical ranking.

At least several seeds per scenario are needed before interpreting differences.
The included one-seed reference files are useful for reproducibility, not for a
strong performance claim.

## Engineering priorities

1. Preserve `policy.py` as the thin JSON process adapter.
2. Put new logic in small modules for features, clarification, scoring,
   allocation and memory updates.
3. Add unit tests for empty state, declined fields, exhausted ask budget,
   reciprocal constraints, repeated pairs, deterministic output and memory size.
4. Keep stdout protocol-only and send diagnostics to stderr.
5. Measure process startup and worst-case request time, not only algorithm time.
6. Build and run the offline container before calling the policy submission-ready.

## Immediate risks

- Tuning directly against inspectable simulator truth or reconstructing generator
  seeds violates the observation contract and risks disqualification.
- Treating no response as rejection biases the learning target.
- Day-30 snapshot values cannot be attached retroactively to earlier outcomes.
- The public outcomes are sparse, so small score changes may be noise.
- A globally better allocation objective can still hurt MSMI if its edge values
  are poorly estimated.
- Windows Git may rewrite line endings in checksum-covered data unless the team
  repository enforces LF; `.gitattributes` now does so.
