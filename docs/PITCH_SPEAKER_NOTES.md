# LuminaX Round 2 speaker notes

The spoken text below matches the presenter notes embedded in the deck. The
timing leaves 40 seconds for handoffs or a slow screen share.

## Slide 1: One introduction, when it is right

**Time:** 0:00 to 0:20
**Speaker:** Ahan

Good morning. We are LuminaX, Ahan Sardar and Enakshee Mondal. Our Round 2
submission is a deterministic policy for sequential matching with incomplete
information. Our goal is simple: ask only when a missing hard constraint blocks
a decision, then make a safe, reproducible daily matching.

## Slide 2: This is an allocation problem

**Time:** 0:20 to 1:05
**Speaker:** Ahan

This problem allocates a daily batch; it does not predict pairs independently.
Every introduction uses two people and removes them from other possible pairs.
Information can be missing, answers can be delayed, and preferences must work
in both directions. The policy must decide what to clarify, which edges are
feasible, and which non-overlapping set to allocate today.

## Slide 3: Our operating principle

**Time:** 1:05 to 1:55
**Speaker:** Ahan

We separate safety from priority. Hard constraints decide whether an edge may
exist. Soft similarities only decide the order among feasible edges. Missing
soft information gives no credit and no penalty. The compatibility score is an
allocation priority, not a probability of success. This separation prevents a
high score from overriding reciprocal eligibility.

## Slide 4: The daily algorithm

**Time:** 1:55 to 2:55
**Speaker:** Ahan

Each day has four steps. First, validate the observable state and fail closed
on malformed or conflicting records. Second, use the clarification budget on
available people with missing hard fields, ordered by arrival day and then by
opaque ID. Third, after the refreshed observation, build the reciprocal
feasible graph. Fourth, count observed equal soft fields, sort edges by that
score and a stable tie-break, and greedily take an edge when both endpoints are
unused. The same observable input always produces the same action.

## Slide 5: One day, step by step

**Time:** 2:55 to 4:10
**Speaker:** Ahan

This example uses four fictional members. D is available but one hard field is
missing, so the policy uses one hard bundle. After the evaluator returns the
refreshed observation, the policy builds only reciprocal feasible edges. A-D
scores 2, while A-B and B-C score 1. The allocator takes A-D first. A-B is then
skipped because A is already used. B-C remains disjoint, so it is also
selected. The output is A-D and B-C. The example is illustrative and uses no
hidden information.

## Slide 6: What the policy guarantees

**Time:** 4:10 to 4:55
**Speaker:** Ahan

The policy guarantees four things at its own boundary: reciprocal hard
constraints are checked before scoring, no person appears twice in a daily
batch, people with open introductions remain blocked, and the policy uses only
the observable request. It does not read hidden truth, private seeds, or member
IDs as outcome features. Opaque IDs are used only to make ties deterministic.

## Slide 7: Public comparison

**Time:** 4:55 to 6:05
**Speaker:** Enakshee

We compared every method on the same three public seed groups and all six
scenario families, for 18 episodes per method. The submitted policy scored
0.4444 MSMI per 100 arrived members. Greedy scored 0.3889, random feasible
0.2778, and no clarification 0.1389. That is 16 qualifying outcomes for our
method versus 14 for greedy. The difference is promising, but the public
sample is small.

## Slide 8: Where the result holds and fails

**Time:** 6:05 to 7:05
**Speaker:** Enakshee

The gain is not uniform. Cold start and shift are the strongest public
scenarios. Development and drift are neutral against greedy. Greedy is better
in delayed and sparse, and our sparse mean is zero. The paired seed-grouped
bootstrap difference from greedy is 0.0556 with a 95 percent interval from zero
to 0.0833. Since the lower end is zero, we do not claim a confirmed private
advantage.

## Slide 9: Why we trust the build

**Time:** 7:05 to 8:00
**Speaker:** Enakshee

We tested the boundary as carefully as the algorithm. The final suite has 125
tests. All 71 public data files validate. The pinned container completed 120
calls in the recorded check, with a slowest call of 1.246 seconds under the
10-second limit. A release gate checks the default method, result hashes,
matrix completeness, container evidence, file allowlist, and immutable tag.
This does not prove a private score, but it sharply reduces avoidable
submission failures.

## Slide 10: What we are submitting

**Time:** 8:00 to 9:20
**Speaker:** Ahan

We are submitting the smallest method that survived our evidence checks:
stable clarification, reciprocal feasibility, observed-soft priority, and
deterministic greedy allocation. We rejected more complex variants when their
gains did not survive matched holdouts or when they lost an official tie-break.
The next research target is sparse supply, where a validated scarcity-aware
clarification or waiting rule could help. Our contribution is a policy whose
decisions, limits, and evidence can all be inspected. Thank you.

Stop here for the main presentation. Slides 11 to 13 are backup material for
questions.

## Backup slide 11: Exact metrics

Use this slide if a judge asks for tie-break metrics, service outcomes, or the
exact scenario table. Lead with the primary score, then follow the official
tie-break order.

## Backup slide 12: Why not a more complex method?

Explain that maximum-cardinality, history-based, learned, waiting-priority,
and graph-aware approaches were tested. They were not promoted because their
gains did not repeat on separate seed blocks or because they harmed an official
tie-break. Complexity was treated as a hypothesis, not as evidence.

## Backup slide 13: Reproduce the evidence

Show the immutable tag, result summary, report, and main commands. If time is
short, point to the tagged repository instead of running the evaluator live.
