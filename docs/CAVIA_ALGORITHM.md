# CAVIA-Match algorithm

CAVIA means **Constraint-Aware Value-of-Information Allocation**. This document
explains the first working prototype in simple terms.

Status: rejected prototype retained for experiment history. It is not the current
competition policy. See [SAFE_CARDINALITY_ALGORITHM.md](SAFE_CARDINALITY_ALGORITHM.md).

## 1. Daily decision flow

Each simulated day has two phases:

1. **Ask phase:** choose which missing hard constraints to clarify.
2. **Match phase:** score feasible pairs and select a non-overlapping batch.

The policy uses only the observable JSON request and the small memory object
returned through the official interface.

## 2. Targeted clarification

The daily clarification budget is 12 units. A hard-constraint bundle costs 3, so
the policy can ask at most four people per day.

For every available person with unasked hard information, CAVIA examines the
currently possible candidate edges. Known-infeasible pairs are ignored. Missing
information is never treated as permission.

The priority score rewards:

- Promising blocked edges.
- Edges that one person's answer could fully resolve.
- People who currently have no feasible edge.
- People with few possible alternatives.
- People who have waited longer.

An edge blocked only by A's missing constraints receives more clarification
value than an edge that also needs information from B. People with declined hard
answers are not repeatedly asked because the declined answer would remain
unknown.

This is an explainable value-of-information proxy. It does not access the hidden
answer or claim to know what the answer will be.

## 3. Reciprocal feasibility

After clarification, CAVIA builds a graph using only feasible pairs.

- Each available person is a node.
- Each feasible pair is an edge.
- Known hard failures remove the edge.
- Missing hard information blocks the edge.
- Previous pairs and unavailable people are excluded.

The official `eligibility` function performs the reciprocal hard checks. CAVIA
never uses a soft score to override them.

## 4. Pair score

Each feasible edge receives this score:

```text
base
+ observed soft compatibility
+ candidate-scarcity bonus
+ waiting bonus
+ mature-feedback signal
- missing-soft-information penalty
```

### Soft compatibility

The prototype gives more weight to relationship goal, pace, emotional
availability and space for a relationship. Lifestyle, conversation style and
relocation preference receive smaller weights.

Only equality on two observed values adds compatibility. A missing value does
not count as a match.

### Scarcity and waiting

A pair receives a small bonus when either person has few feasible alternatives.
It also receives a capped bonus when the two people have waited longer.

These bonuses cannot make an infeasible edge valid. They only break competition
between already feasible edges.

### Uncertainty

Missing soft fields create a penalty. This makes the policy less confident about
poorly observed pairs without turning missing information into a negative answer.

### Mature feedback

CAVIA separates two operational outcomes:

- Both introduction responses were recorded Yes by the response deadline.
- The complete MSMI outcome was observed after its full maturity window.

Recent mature outcomes receive more weight than old outcomes. This gives the
prototype a simple response to changing conditions. A missing response is used
only as absence of the defined recorded-Yes event; it is never described as
dislike or rejection.

Historical soft fields are used only when their observation day is no later than
the original assignment day. This prevents later answers from leaking into an
earlier decision.

## 5. Batch allocation

CAVIA first performs deterministic greedy matching using the edge scores.

It then checks pairs of selected edges for a better exchange.

Example:

| Edge | Score |
|---|---:|
| A-B | 0.90 |
| C-D | 0.05 |
| A-D | 0.65 |
| B-C | 0.65 |

Greedy gives A-B and C-D, worth 0.95. The exchange gives A-D and B-C, worth
1.30, so CAVIA replaces the two edges.

The local search repeats deterministic best exchanges until no improvement is
found or the safety limit is reached. Every result remains non-overlapping.

This prototype does not yet claim exact global maximum-weight matching. The
local improvement is smaller, easier to audit and dependency-free.

## 6. Policy memory

The returned memory contains only:

- CAVIA version.
- Current day.
- Number of mature mutual-response outcomes.
- Number of mature MSMI outcomes.

The memory stays small and contains no hidden simulator information. Observable
cumulative history is re-read from each request, so the policy does not depend on
persistent files.

## 7. Available experiment modes

| Mode | Purpose |
|---|---|
| `cavia` | Full prototype |
| `cavia_no_targeted_asks` | Starter asks instead of targeted asks |
| `cavia_greedy` | Greedy allocation without two-edge exchanges |
| `cavia_no_uncertainty` | Removes the missing-soft-data penalty |
| `cavia_no_feedback` | Removes mature-feedback learning |
| `cavia_targeted_baseline` | Targeted asks with the supplied pair ranking |
| `greedy` | Supplied baseline |
| `no_asks` | Supplied no-clarification baseline |
| `random` | Supplied random-feasible baseline |

Example smoke comparison:

```powershell
python evaluate.py --baseline cavia --seeds 101 --output results/cavia_smoke.json
python evaluate.py --baseline greedy --seeds 101 --output results/greedy_smoke.json
```

Use identical seeds and variants for every serious comparison.

## 8. Complexity and limits

Pair construction checks at most all pairs of available members. With 200
members, this is manageable. Two-edge improvement compares pairs of selected
edges and stops after at most 12 exchanges.

The implementation uses only the Python standard library. It requires no
network, model download, external API or GPU.

## 9. Known limitations

- The value-of-information calculation is a proxy, not a full counterfactual
  expectation over possible answers.
- Pair weights are hand-designed and have not yet been calibrated on validation
  runs.
- Feedback buckets are intentionally simple because mature MSMI outcomes are
  sparse.
- Two-edge exchange can improve greedy allocation but is not guaranteed to find
  the global optimum.
- Waiting uses current scarcity and time already waited; the policy cannot see
  future arrivals.
- Performance claims require matched-seed experiments and ablations.
