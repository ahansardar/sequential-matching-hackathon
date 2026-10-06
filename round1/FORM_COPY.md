# Google Form copy sheet

The organiser has not published the Round 1 form yet. Its exact questions may be
different. Use these answers as a simple copy source and adapt them to the actual
fields. Replace every `[TODO]` before submission.

## Team name

[TODO]

## Team members

- [TODO: full name of member 1]
- [TODO: full name of member 2]

## Contact email

[TODO]

## Project title

Constraint-First Sequential Matching with Targeted Clarification

## Short project summary

We propose a sequential matching policy that first enforces every reciprocal hard
constraint, then uses the daily question budget only where new information could
change a useful decision. Feasible pairs are ranked using observed compatibility,
candidate scarcity and uncertainty. The policy chooses a non-overlapping daily
batch and tests small improvements over greedy selection. We will compare the
method with the supplied greedy, no-clarification and random-feasible baselines on
the same seeds and all six public scenarios. We will also test clarification and
allocation ablations. Missing responses will remain missing, and hidden or future
simulator information will never be used.

## Main hypothesis

Targeted clarification, reciprocal scoring and improved batch allocation will
increase Mutual Second-Meeting Intention compared with greedy matching. We expect
the largest benefit when information or feasible candidates are scarce.

## Proposed clarification method

We will rank asks by the number and quality of blocked edges they may unlock, the
member's lack of alternatives, whether the answer can change today's decision and
the ask cost. Missing hard information will block a match, and declined answers
will remain unavailable.

## Proposed matching method

We will build a graph containing only reciprocally feasible pairs. Each edge will
receive an explainable score based on currently observed soft compatibility,
candidate scarcity, mature feedback and uncertainty. We will begin with greedy
selection and then test deterministic two-edge exchanges that improve the total
batch value.

## Handling missing and delayed data

Unknown, declined and observed answers remain separate. No response is not
treated as rejection. Recent outcomes are not labelled until their observation
window is mature. The policy will use only information observable at the time of
each action.

## Baselines

- Supplied greedy policy.
- Supplied no-clarification policy.
- Supplied random-feasible policy.

All methods will use identical declared seeds and the same six scenario families.

## Planned ablations

- Replace targeted asks with the starter's first-come asks.
- Replace improved allocation with greedy allocation.
- Remove the uncertainty penalty from pair scoring.

## Main risks

The method may struggle with sparse geography, declined constraints, delayed
feedback, changing outcome behaviour and very low MSMI counts. Improvements on a
small number of public seeds may not generalise to private evaluation.

## Current results

The supplied reference files show one-seed smoke results only. Our team-policy
results are not yet available. We will not present planned or simulated values as
completed evidence.

## Document link

[TODO: add the fixed Markdown or PDF link requested by the form]

## Repository link

[TODO: add only if the form requests it]
