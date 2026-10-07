# Learned outcome-scoring experiment

Status: rejected for the submission runtime.

We tested whether a fitted outcome score could beat the current transparent
compatibility score. It did not improve consistently on untouched seeds, so the
default policy remains safe-cardinality.

## What we trained

The training script generated valid matching episodes on seeds 2001 through
2040 across all six public scenario types. It recorded 18,149 introductions.

For each introduction, the script saved only information that was observable
when the pair was selected:

- whether each soft field matched, differed or was unknown;
- earlier introduction-response counts;
- earlier accepted-introduction counts; and
- earlier on-time positive second-meeting counts.

It attached the outcome label only after the feedback window matured. It did
not use hidden member truth, private coefficients, member IDs as features or
future feedback in an earlier feature row.

Run the trainer with:

```text
python experiments/train_outcome_model.py --seeds 2001-2040 --variants all --workers 4 --output outcome_model.json
```

The script writes its large local training table under `results/`, which Git
ignores. The fitted `outcome_model.json` is small and committed so another team
member can inspect the exact coefficients without retraining.

## Models compared

We tested four scoring shapes:

| Model | Simple meaning |
|---|---|
| Static direct | Predict final MSMI from observed soft-field comparisons |
| History direct | Add each person's earlier observable feedback rates |
| Decomposed funnel | Estimate response, acceptance, date and second interest separately |
| Guarded funnel | Use the funnel score only when the old compatibility total does not fall |

Every model still used the official reciprocal feasibility check. A predicted
score never created an edge that failed a hard constraint.

## Results

All comparisons used identical seeds and scenario variants for both methods.

| Block | Episodes | Learned | Safe policy | Difference |
|---|---:|---:|---:|---:|
| Tuning screen, history model | 60 | 0.467 | 0.350 | +0.117 |
| Untouched history holdout | 120 | 0.417 | 0.508 | -0.092 |
| Untouched static holdout | 120 | 0.325 | 0.300 | +0.025 |
| Static confirmation block | 120 | 0.317 | 0.358 | -0.042 |

The history holdout loss was clear in this sample. Its paired 95% normal
interval was -0.167 to -0.017. The static model's two holdouts disagreed, and
both intervals included zero.

The complete scenario-level and paired results are in
`results/learned_model_selection_summary.json`. The raw experiment outputs are
kept locally under `results/` and can be regenerated with
`experiments/compare_policies.py`.

## Decision

Do not use a tuning win as proof of a better policy. Neither learned scorer
repeated its improvement. Shipping one would add model risk without reliable
score gain.

The experiment code and fitted asset remain in the repository for review. The
Docker image does not include them, and `policy.py` does not expose learned
modes. The submitted algorithm stays deterministic, dependency-free and based
only on the current safe-cardinality method.
