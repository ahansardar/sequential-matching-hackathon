# Confidence audit

## Purpose

`experiments/confidence_audit.py` compares an incumbent and a challenger on
identical seeds and scenario variants. It reports the official summaries, the
paired score difference, scenario differences and a deterministic 95% paired
bootstrap interval.

The script uses only simulator observations. It is a fast research check. A
successful candidate must still pass the official subprocess and container
evaluation.

## Strong-evidence rule

The script marks `promote` true only when all four checks pass:

1. Every episode from both policies is valid.
2. The challenger's primary score is higher.
3. The lower end of the paired 95% interval is above zero.
4. No scenario family has a lower mean score.

This is intentionally strict. The field is an evidence grade, not an automatic
deployment command. If the interval includes zero, the experiment does not
support a strong improvement claim. A competition team may still choose the
higher point estimate, but it must label the gain uncertain.

The day-20 history policy illustrates this distinction. It scored 0.2708 versus
0.2500 on 120 untouched episodes, but its paired 95% interval was -0.0167 to
0.0583. The strong-evidence gate fails because the interval includes zero.

## Example

```text
python experiments/confidence_audit.py ^
  --incumbent adaptive ^
  --challenger adaptive_legacy ^
  --seeds 4001,4002,4003,4004,4005 ^
  --variants all ^
  --workers 4 ^
  --output results/confidence_audit.json
```

Use tuning seeds for early comparisons. If a challenger passes, run it once on
a separate untouched confirmation block before changing the submission
default. Results belong under `results/`, which is excluded from Git.

## Latest objective-separation result

We tested two challengers on seeds 5201-5210 across all six public scenario
families.

| Policy | MSMI score | Coverage | Mutual acceptances per 100 |
|---|---:|---:|---:|
| Current `adaptive` | 0.2833 | 0.3326 | 5.2583 |
| Fully separated objectives | 0.2750 | 0.3326 | 5.2417 |
| Raw-compatibility guard only | 0.2833 | 0.3326 | 5.2417 |

The fully separated policy lost the primary metric. The isolated guard tied the
primary metric but lost the mutual-acceptance tie-break. We kept the current
policy.
