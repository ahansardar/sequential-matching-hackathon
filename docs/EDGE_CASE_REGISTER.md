# Edge-case register

This register separates three things:

- cases the submitted policy must handle;
- cases the evidence code must measure correctly;
- malformed inputs that are outside the published contract.

No finite test suite proves that every imaginable failure is impossible. The
goal is narrower and useful: cover every boundary in the published rules, the
organiser feedback, and the failure paths we can reach in this repository.

## Submitted policy

| Case | Required behavior | Protection |
|---|---|---|
| No members | Return no asks and no pairs. | Unit test and edge-case audit. |
| No feasible edge | Return an empty pair list. | Existing policy tests and container evaluation. |
| Fully connected 200-member graph | Return 100 non-overlapping pairs inside the time and output limits. | Real-process dense-graph test. |
| Member list reordered | Return the same asks and pairs. | Stable clarification order by arrival day and opaque ID; permutation audit. |
| Feedback, introduction or ask-log order changed | Return the same submitted-policy action. | Submitted mode does not depend on list order; permutation audit. |
| Constraint arrays reordered | Preserve the same eligibility result. | Membership and set-overlap checks; permutation audit. |
| Equal pair scores | Break ties deterministically by canonical pair ID. | Sorted pair keys. IDs are used only as a tie-break, never as a feature. |
| Pair endpoints reversed | Treat the pair as the same pair. | Canonical sorted pair keys. |
| Repeated pair | Never propose a pair already present in introductions. | Past-pair set checked before allocation. |
| Same member twice | Never create a self-pair. | Reciprocal eligibility rejects it. |
| One person in two pairs | Never reuse a person in a daily batch. | Greedy allocator keeps a used-member set. |
| Unknown or unavailable member | Never ask or match them. | Ask filter and available-member filter. |
| Different pools | Never match across pools. | Reciprocal eligibility check. |
| Known hard failure plus missing fields | Treat the pair as infeasible, not merely unknown. | Eligibility gives a known failure priority. |
| Unknown hard field | Do not match until clarified. | Only fully known hard constraints enter the feasible graph. |
| Declined hard field | Do not ask again and do not infer an answer. | Declined status blocks the hard bundle. |
| Unknown soft field | Give no match credit and do not treat it as disagreement. | Compatibility counts only two observed equal values. |
| Ask budgets 0, 1 or 2 | Ask nobody. | Integer bundle cost and boundary tests. |
| Ask budgets 3 through 11 | Submit only the number of complete bundles that fit. | Floor division and boundary tests. |
| Ask budget 12 | Submit at most four hard bundles. | Boundary tests. |
| Duplicate member row | Do not emit duplicate asks. | Ask candidates are keyed by member ID. |
| Conflicting duplicate member rows | Exclude that ID instead of trusting the first copy. | Consistency grouping and reversed-order test. |
| Old, scalar or list memory | Reinitialize safe policy memory. | Memory type guard and tests. |
| Exact request is replayed | Return the same action and compact memory. | Idempotence and memory-size test. |
| Extra future JSON fields | Ignore fields the v1 policy does not use. | Forward-compatibility test. |
| Ignored future data brings the request near 1 MiB | Parse it inside the time limit without echoing it into memory. | Near-limit real-process test. |
| Python hash randomization changes | Return byte-equivalent actions under different `PYTHONHASHSEED` values. | Two-process determinism test. |
| Several pools and a reversed historical pair coexist | Never cross pools or repeat the historical pair. | Combined boundary test. |
| Unusual valid-state combinations | Preserve availability, feasibility, novelty and non-overlap invariants. | Eighty deterministic randomized states. |
| Empty, sparse and dense graphs | Stay deterministic and within the public limits. | Edge-case audit plus release container check. |
| Non-finite output | Never emit NaN or Infinity. | `allow_nan=False` and response validation. |
| Protocol noise | Write one JSON object to stdout. | Real-process tests and container evaluation. |
| Offline execution | Make no network call and require no persistent files. | Standard-library runtime and isolated Docker run. |

## Time and feedback

| Case | Required behavior | Protection |
|---|---|---|
| Response on day 7 | Count it as on time. | Inclusive deadline test. |
| Response after day 7 | Do not count it in the Yes-by-deadline target. | Strict event helper. |
| Date on day 30 after assignment | Count it inside the MSMI date window. | Inclusive boundary test. |
| Date after day 30 | Do not count MSMI. | Strict event helper. |
| Second intention on day 3 after the date | Count it inside the MSMI window. | Inclusive boundary test. |
| Second intention after day 3 | Do not count MSMI. | Strict event helper. |
| Event before assignment or before the date | Do not count it. | Lower-bound checks. |
| Date occurs before both positive responses | Keep mutual acceptance but do not count a date or MSMI. | Causal-order check. |
| Member-scoped event names a third person | Reject the evidence as corrupted. | Endpoint validation. |
| Pair-level date event names a member | Reject the evidence as corrupted. | Pair-level actor validation. |
| JSON boolean appears where a day integer is required | Do not treat it as day 0 or 1. | Exact integer-type check. |
| No response at the deadline | Label the defined Yes-by-deadline event as 0, not personal dislike. | Target definition retained in the report. |
| Recent unresolved introduction | Keep it out of mature calibration labels. | Forty-day follow-up and maturity assertion. |
| Duplicate or contradictory event | Reject the evidence instead of choosing a convenient record. | Strict one-event-per-type/member check. |
| Delayed observed day | Require the event to be observable inside the target window. | Occurred-day and observed-day checks. |

## Statistical evidence

| Case | Required behavior | Protection |
|---|---|---|
| Six variants share one generated seed world | Resample the whole seed group. | Seed-clustered bootstrap. |
| Variants create different assignment counts | Give each scenario family equal weight. | Equal-variant calibration metrics and intervals. |
| Duplicate or missing seed/variant block | Stop validation. | Rectangular-block validator. |
| Fit, calibration and holdout overlap | Stop validation. | Disjoint split check. |
| One class is absent | Report AUC as undefined. | Calibration metric test. |
| Fixed-width bins hide sparse regions | Also report equal-count bins and ECE. | Holdout calibration output. |
| Calibration looks better by chance | Compare paired Brier differences by seed group. | Paired intervals against raw and constant predictors. |
| Endpoint orientation differs | Apply the same directional estimator after swapping actor and candidate. | Separate `user_a` and `user_b` diagnostics. |
| Small subgroup | Report its count and avoid a precision claim from the point estimate alone. | Subgroup output retains examples and positives. |
| Many tried algorithms | Keep failed challengers out of runtime and record them. | Decision log and untouched holdouts. |

## Service and profile information

| Case | Required behavior | Protection |
|---|---|---|
| A sparse profile also arrived late | Separate arrival band from profile band. | Service cells cross both bands. |
| A sparse profile had no plausible partner | Separate opportunity scarcity from service choice. | Initial not-ruled-out partner count and opportunity band. |
| Missing hard data looks like no opportunity | Report both decidable feasible and not-ruled-out partners. | Two opportunity measures with an explicit limitation. |
| A cohort is empty | Return no invented rate. | Empty cohort rates remain null or are omitted. |
| A member is never served | Keep the member in coverage and unserved denominators. | Decision-horizon denominator. |
| A served member has several introductions | Count the member once for coverage and first wait. | Distinct-member aggregation. |
| Soft-field masking changes hidden truth | Never do this. Mask only the policy observation. | Deep-copy mask tests; world and outcome process stay fixed. |

## Outside the promise

The policy assumes a valid v1 request because the organiser validates the
contract. Invalid UTF-8, missing required member fields, non-string IDs,
non-integer days and requests larger than 1 MiB are rejected by the harness or
container boundary. The policy does not try to repair them.

The public simulator cannot prove performance on private worlds. These checks
protect validity, reproducibility and honest analysis. They do not guarantee a
particular private MSMI score or selection decision.

## Rerun

```text
python -m unittest -v test_edge_cases.py
python experiments/edge_case_audit.py --output results/edge_case_audit.json
python experiments/validate_corrected_addendum.py
```
