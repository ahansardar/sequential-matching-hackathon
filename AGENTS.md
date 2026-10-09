# Working rules for agents

These rules apply to the whole repository.

## Understand the task first

- Read `PROBLEM_STATEMENT.md`, `docs/POLICY_INTERFACE.md` and
  `docs/DATA_CONTRACT.md` before changing the policy.
- Read `docs/DECISIONS.md` before replacing an accepted method.
- Use only the observable policy request. Never read hidden simulator truth,
  recover private seeds or infer answers from member IDs.

## Work with the team

- Make changes on a person's named branch. Do not put tool names in branch
  names, source files, documentation or commits.
- Give one person ownership of a task and let the teammate review it.
- Do not edit the same file at the same time. Split work by file or feature.
- Keep commits small and explain the reason for each change.
- Never overwrite a teammate's uncommitted work.

## Compare algorithms fairly

- Run competing methods on identical seeds and scenario variants.
- Keep tuning seeds separate from the final untouched holdout.
- Judge the primary MSMI score first. Use coverage, mutual acceptance, ask cost
  and runtime only in the official tie-break order.
- Treat a small result as uncertain. Do not call one lucky seed a win.
- Record rejected ideas in `docs/DECISIONS.md` instead of leaving them in the
  submission runtime.

## Protect the submission

- Keep `policy.py` as the JSON entry point and write only protocol JSON to
  standard output.
- Preserve reciprocal hard constraints. A score never overrides feasibility.
- Keep the policy deterministic, offline and within the published limits.
- Do not commit secrets, private organiser data, caches or personal data.
- Before pushing a submission change, run:

```text
python -m unittest -v
python verify_data.py
docker build -t sequential-policy:submission .
python evaluate.py --image sequential-policy:submission --seeds 101 --variants development --output results/container_check.json
```

- A passing public run proves interface and packaging validity. It does not
  guarantee a private score or a competition win.
