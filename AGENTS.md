# Agent collaboration rules

These instructions apply to every automated agent working anywhere in this
repository. They supplement the challenge rules in `PROBLEM_STATEMENT.md` and the
team process in `CONTRIBUTING.md`.

## 1. Start by understanding the task

Before editing:

1. Read the user request carefully.
2. Read the relevant parts of `PROBLEM_STATEMENT.md`, `docs/DATA_CONTRACT.md`,
   `docs/POLICY_INTERFACE.md` and `docs/SUBMISSION.md`.
3. Read `CONTRIBUTING.md`, `docs/TEAM_WORKFLOW.md` and
   `docs/DECISIONS.md`.
4. Check the current branch and working-tree status.
5. Inspect related code, tests, documentation and open work before proposing a
   change.

Do not turn a documentation or design request into an unrelated implementation.
Do not overwrite, discard or reformat another contributor's unfinished work.

## 2. Work on one owned task

- Keep each task focused on one hypothesis, feature, experiment, fix or document.
- Use an existing Issue when one covers the work. Otherwise state the task scope
  clearly before starting.
- One contributor owns the change. The other teammate reviews its assumptions,
  correctness and evidence.
- Avoid editing files currently owned by another active task. If overlap is
  necessary, coordinate first.
- Record important methodology or contract decisions in `docs/DECISIONS.md`.

## 3. Git and branch rules

- Never commit directly to `main`.
- Use a short-lived branch named `research/<topic>`, `policy/<topic>`,
  `experiment/<topic>`, `docs/<topic>`, `fix/<topic>` or
  `chore/<topic>`.
- Keep `origin` for the team repository and `upstream` for the official starter.
- Never push team work to `upstream`.
- Fetch and review upstream corrections in a separate
  `chore/upstream-sync` branch.
- Do not force-push, rewrite shared history, delete branches or discard local
  changes unless the user explicitly requests it.
- Use small commits with messages that explain the purpose of the change.
- Open a pull request and leave it for the other teammate to review. Do not merge
  your own work unless the user explicitly asks or the team has recorded an
  exception.

## 4. Preserve the challenge contract

Every policy change must follow these rules:

- Use only the observable request state, clarification results, visible feedback
  and policy-owned memory.
- Never read hidden simulator fields, future arrivals, generator seeds, latent
  values, organiser files or private evaluation data.
- Never reconstruct missing answers from identifiers or public generation code.
- Check reciprocal hard feasibility before scoring or allocation.
- Missing hard information blocks a match. Declined information stays unknown.
- A high soft score never overrides a hard constraint.
- Keep assignment, response, mutual acceptance, date and second-meeting intention
  as separate events.
- Missing feedback is not a rejection. Unresolved outcomes are not completed
  failures.
- Support empty populations, empty feasible graphs, empty asks and empty pair
  lists.
- Never propose repeated, overlapping, unavailable or cross-pool pairs.
- Keep standard output limited to the required JSON response. Send diagnostics
  to standard error.
- Keep request, response and memory values finite and within the official size
  limits.
- Evaluated inference must work offline on CPU within the official process,
  memory, image-size and 10-second invocation limits.

## 5. Data and experiment discipline

Use the public static pools only as follows:

- `public_01` to `public_06`: training and method development.
- `public_07` and `public_08`: validation and model selection.
- `public_09` and `public_10`: final development test. Do not repeatedly tune on
  them.

For simulator experiments:

- Declare every seed before running the comparison.
- Compare methods on identical seeds and variants.
- Include all six public variants for serious comparisons.
- Compare against greedy, no-asks and random-feasible baselines.
- Keep raw machine-readable results. Never edit result JSON by hand.
- Do not select only favourable runs.
- Separate exploratory, validation and final-confirmation results.
- Report zero scores, invalid episodes, missing feedback and unserved members.
- Record the exact command and Git commit for important runs.
- Treat a one-seed result as a smoke test, not a performance conclusion.

## 6. Evidence and writing rules

- Use simple language, short explanations and small examples.
- Clearly label work as proposed, implemented, tested or unverified.
- Do not present a plan, fixture, parser result or passing unit test as evidence of
  policy improvement.
- Do not claim a policy is better until matched-seed results support the claim.
- Keep synthetic simulator results separate from claims about real people or a
  real product.
- State assumptions, uncertainty, failure cases and limitations.
- Do not fabricate citations, results, team details, form fields or submission
  confirmations.
- Preserve the distinction between required challenge rules and team proposals.
- Never include secrets, access tokens, personal dating information or private
  organiser material.

## 7. Verification requirements

For any code or policy change, run at least:

```powershell
python -m unittest -v
python verify_data.py
python evaluate.py --seeds 101 --output results/smoke.json
```

For a submission candidate, also run:

```powershell
docker build -t sequential-policy:submission .
python evaluate.py --image sequential-policy:submission --seeds 101 --output results/container_check.json
```

For documentation-only changes:

- Run `git diff --check`.
- Check all local Markdown links and remaining placeholders.
- Run the unit tests and data verification when practical.
- Confirm that dates, deadlines and submission routes still match the latest
  official upstream guidance.

If Docker or another required tool is unavailable locally, report that clearly
and use the repository's CI result as evidence when available. A passing public
smoke test does not guarantee success on private evaluation.

## 8. Pull request handoff

Every pull request should state:

- The problem or hypothesis addressed.
- What changed and what did not change.
- Files that need the closest review.
- Commands that were run and their results.
- Seeds and variants used for any experiment.
- Known limitations, risks and unfinished work.
- Whether results are exploratory, validation or final confirmation.

The reviewer should check challenge compliance, leakage risk, hard feasibility,
fair comparisons, claims, edge cases and reproducibility. Merge only after the
relevant checks pass and review comments are resolved.

## 9. Submission safety

- Keep the team repository private during development unless the user decides
  otherwise.
- Do not change repository visibility, invite collaborators, publish releases or
  submit forms without explicit user authorization.
- Before Round 1 submission, remove every placeholder and freeze the exact
  Markdown or PDF version.
- Before Round 2 submission, verify the public repository or immutable archive,
  full commit SHA or checksum, report, result JSON, licences and container.
- Save submission receipts and record the exact submitted version and time.

## 10. Definition of done

A task is complete only when:

- The requested scope is fully addressed.
- Challenge and interface contracts remain valid.
- Relevant tests and evaluations pass.
- Claims match the available evidence.
- Documentation and decision records are updated.
- The working tree contains no accidental files or unrelated changes.
- The pull request gives the teammate enough information to review and reproduce
  the work.
