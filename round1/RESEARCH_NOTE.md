# Constraint-First Sequential Matching with Targeted Clarification

## Submission details

- **Team name:** [TODO]
- **Team members:** [TODO: member 1], [TODO: member 2]
- **Contact email:** [TODO]
- **Repository:** [TODO: add the public or shared link requested by the form]
- **Document version:** 0.1
- **Date:** 5 October 2026

## 1. Short summary

We propose a matching policy that first protects every person's stated hard
constraints, then asks only the questions that are likely to improve the next
decision. Feasible pairs receive a reciprocal score based only on information
available at that time. The policy then chooses a group of non-overlapping pairs
for the day instead of choosing each pair independently.

Our main hypothesis is that targeted clarification and better batch allocation
will produce more Mutual Second-Meeting Intention outcomes than the supplied
greedy policy. We expect the largest benefit in cold-start and sparse-supply
settings, where information and good alternatives are limited.

This is a research proposal. The full team policy and its results have not yet
been completed. Any preliminary result added later will be labelled clearly.

## 2. Problem in simple words

Each day, the system sees the people who have arrived and the information that is
currently known about them. It can spend a small budget to clarify missing
answers. It can then introduce feasible pairs, wait, or do both for different
people.

The problem is difficult for four reasons:

1. Both people must satisfy each other's constraints.
2. Some information is missing, declined or learned later.
3. A person can be used in only one pair in a daily batch.
4. Feedback arrives after the decision and only for pairs that were selected.

The main score is Mutual Second-Meeting Intention, or MSMI, per 100 arrived
members. A pair counts only when both accept the introduction, a date happens
within the required window, and both give an on-time Yes for meeting again.

## 3. Research question and hypothesis

### Research question

Can a constraint-first policy improve MSMI by spending clarification budget on
high-value uncertainty and choosing the whole daily batch more carefully?

### Main hypothesis

A policy with these three parts will outperform the supplied greedy baseline:

1. Targeted clarification based on likely decision value.
2. Reciprocal pair scoring with an explicit uncertainty penalty.
3. Batch allocation with local improvements over greedy edge selection.

### Expected result

We expect the full method to improve MSMI without causing invalid episodes. We
also expect targeted clarification to improve coverage in cold-start settings and
better allocation to help when several strong pairs compete for the same person.
These are hypotheses, not measured claims.

## 4. Information the policy may use

The policy will use only the observable JSON state supplied at the time of the
decision:

- Arrived member identifiers and current availability.
- Age, stated gender and fictional zone.
- Observed hard constraints and their status.
- Observed soft questionnaire fields.
- Previous introductions and currently observable feedback.
- Clarification history.
- Policy memory returned through the official interface.

The policy will not read hidden simulator fields, future arrivals, latent values,
private seeds or organiser files. It will not reconstruct missing answers from
identifiers or public data-generation code.

## 5. Reciprocal feasibility

Hard constraints are checked before a pair receives a score. The check works in
both directions.

For example, A accepting B's age is not enough. B must also accept A's age. The
same rule applies to stated genders to meet, zones, schedules, relationship
structure, smoking and children-related constraints.

A known hard failure makes the pair infeasible. Missing hard information blocks
the pair until it is clarified. A declined answer stays unavailable. A high soft
score can never override a hard constraint.

The policy will also reject:

- A person matched with themselves.
- People from different pools.
- Unavailable people.
- A repeated pair.
- A person used twice in the same batch.
- A person with an outstanding introduction.

## 6. Proposed clarification strategy

The daily clarification budget is 12 units. A hard-constraint bundle costs 3
units and one soft field costs 1 unit.

The supplied baseline asks the first eligible people it finds. Our policy will
rank possible asks by expected decision value.

For each possible hard-constraint ask, we will estimate:

- How many currently blocked candidate edges it could resolve.
- How promising those edges appear from information already observed.
- How few alternatives the member has.
- Whether the answer could change today's allocation.
- The cost of the ask.

A simple initial priority is:

`ask value = promising blocked edges × scarcity × decision relevance ÷ cost`

Example: suppose member A has five feasible alternatives, while member B has no
feasible edge but three promising edges blocked only by B's missing hard
constraints. Asking B is more useful than asking A because it may unlock choices
for a person who currently has none.

Soft questions will be asked only when the answer could change the order of
otherwise feasible pairs. We will not spend the full budget merely because it is
available.

## 7. Proposed pair score

The first version will be simple and explainable. It will combine:

- Agreement on observed relationship goals and pace.
- Agreement on lifestyle and conversation preferences.
- Emotional availability and space for a relationship.
- Relevant observable feedback from mature previous outcomes.
- Candidate scarcity, so a person with few alternatives is not always displaced.
- An uncertainty penalty when important soft information is missing.

If we later estimate probabilities, we will keep directions separate:

- Probability that A accepts B.
- Probability that B accepts A.
- Probability of the declared joint or downstream outcome.

We will state the target and observation window for every probability. We will
not multiply directional probabilities unless we explicitly accept and test an
independence assumption.

Missing feedback is not a rejection. An unresolved recent outcome is not used as
a completed negative label.

## 8. Batch allocation

The supplied greedy method selects the highest edge and continues until no more
non-overlapping edges remain. This can miss a better combination.

Simple example:

| Pair | Value |
|---|---:|
| A-B | 0.90 |
| C-D | 0.05 |
| A-D | 0.65 |
| B-C | 0.65 |

Greedy selection gives A-B and C-D, with total value 0.95. Selecting A-D and B-C
gives 1.30.

Our first implementation will start with greedy matching and then test safe
two-edge exchanges. If replacing two selected edges with two non-overlapping
feasible edges improves the total objective, the policy will make the exchange.
The result will be deterministic for the same request and memory.

We may test exact maximum-weight matching later, but only if its dependency,
licence, container size and worst-case runtime fit the competition limits.

## 9. When the policy waits

Waiting means leaving a person out of today's batch. The policy may wait when:

- No feasible candidate exists.
- Important hard information is still missing.
- Every available edge has weak evidence and clarification may change the choice.
- The person already has an outstanding introduction.
- Selecting the edge would harm the total daily allocation.

The policy cannot see future arrivals. Any waiting rule will use only current
observations, past arrival patterns learned from permitted training runs and
policy memory.

## 10. Learning from delayed feedback

Feedback is both delayed and selective. We observe results only for the pairs the
policy chooses.

The policy will update memory only when the relevant observation window is
mature. It will keep introduction response, mutual acceptance, date occurrence
and second-meeting intention as separate events.

The initial method will use simple counts or smoothed rates from permitted
training rollouts. More complex learning will be added only if it shows a clear
validation benefit. We will not claim unbiased causal estimates because logging
propensities are not supplied.

## 11. Experiment plan

We will compare these methods on identical simulator seeds and all six public
scenario families:

1. Supplied greedy baseline.
2. Supplied no-clarification baseline.
3. Supplied random-feasible baseline.
4. Full team policy.
5. Team policy with targeted clarification disabled.
6. Team policy with allocation improvement disabled.

The six scenarios are development, sparse, cold start, delayed, shift and drift.
We will use separate seed sets for development, validation and final confirmation.
We will not report only favourable seeds.

For every method and scenario, we will record:

- MSMI per 100 arrived members.
- Assignments and distinct-member coverage.
- Mutual acceptances and dates.
- First-introduction waiting time and unserved count.
- Clarification cost.
- Missing feedback.
- Runtime and invalid episodes.

Detailed commands, seed groups and reporting rules are in
`round1/EXPERIMENT_PLAN.md`.

## 12. Ablations

The main ablations test whether each design choice causes a useful difference:

### Ablation A: clarification

Replace targeted clarification with the starter's first-come rule. This tests
whether ask prioritisation matters.

### Ablation B: allocation

Turn off two-edge improvements and keep greedy allocation. This tests whether
batch-level optimisation matters.

### Ablation C: uncertainty

Remove the uncertainty penalty while keeping the rest of the pair score. This
tests whether explicit missingness handling improves decisions.

## 13. Expected failure cases

The policy may struggle when:

- Geography and schedules leave very few feasible pairs.
- Important hard answers are declined.
- Several people depend on the same scarce candidate.
- Feedback arrives too late to help within the decision horizon.
- Outcome behaviour shifts after the policy has learned older patterns.
- The number of MSMI outcomes is too small to separate methods reliably.

We will report these cases rather than hiding unserved members or zero-score
episodes.

## 14. Safety, fairness and limitations

The supplied people and outcomes are synthetic. Simulator results are not proof
that the method predicts real relationships.

Age, stated gender and other sensitive-looking fields are used only according to
the explicit synthetic preference contract. They do not imply unstated
preferences. Hard constraints remain user-controlled and reciprocal.

A real deployment would require authorised data, privacy review, fairness
testing, monitoring, human oversight and separate validation. It would also need
a process for corrections, consent and appeals. None of those real-world claims
can be established from this simulator.

## 15. Reproducibility

The final build will declare:

- Python and dependency versions.
- Training and evaluation seeds.
- Inference randomness, if any.
- Commands used for every reported result.
- External data, models and coding tools.
- Licences for all dependencies and assets.

The policy must run offline on CPU within the official memory, process, response
size and 10-second invocation limits. Standard output will contain protocol JSON
only; diagnostics will go to standard error.

## 16. Current evidence

The organiser includes one-seed reference runs. They are smoke-test results, not
reliable leaderboard estimates.

| Supplied method | Primary score | Coverage | Mutual acceptances per 100 | Ask cost |
|---|---:|---:|---:|---:|
| Greedy | 0.500 | 0.408 | 7.583 | 205 |
| No clarification | 0.333 | 0.174 | 2.833 | 0 |
| Random feasible | 0.250 | 0.412 | 6.667 | 205 |

These results suggest that clarification expands coverage and that pair ranking
matters, but one seed is not enough for a strong conclusion. Team-policy results
will be added only after fair multi-seed evaluation.

## 17. Round 1 conclusion

Our proposal focuses on three decisions: what to clarify, which pairs to value,
and how to choose the daily batch. The method keeps hard reciprocal constraints
separate from soft ranking and treats missing or delayed information explicitly.

The Round 2 build will test whether each component improves outcomes through
matched-seed baseline comparisons and ablations. Our priority is a valid,
reproducible and explainable policy rather than an unnecessarily complex model.

## References

1. The Sequential Matching Problem, participant specification 1.0.0.
2. Policy interface 1.0.0.
3. Data contract 1.0.0.
4. Organiser-supplied baseline result files.
