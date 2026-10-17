# LuminaX pitch Q&A

Keep each first answer under 30 seconds. Give more detail only if the judge asks.

## 1. What is the core idea?

We separate feasibility from priority. Reciprocal hard constraints decide
whether a pair is allowed. Observed soft similarity ranks only the allowed
pairs. We ask about missing hard information before building the graph.

## 2. What is novel about the submission?

The main contribution is the evidence-backed combination of stable
clarification, reciprocal graph construction, deterministic allocation, and a
fail-closed release boundary. We do not claim that greedy matching itself is
novel.

## 3. Why use a greedy allocator?

More complex allocation variants did not show a repeatable gain on separate
seed blocks, and one tied the primary score while losing coverage. Greedy was
the strongest supported choice at freeze time.

## 4. Why not use machine learning?

A learned outcome scorer was tested, but it did not earn promotion on the
declared validation boundary. With limited synthetic evidence, a model would
add complexity without a supported advantage.

## 5. Can a high score override a preference?

No. The official reciprocal eligibility check runs before scoring. An
infeasible pair never enters the candidate edge list.

## 6. What does the pair score mean?

It is the count of observed equal soft fields. It is an allocation priority,
not a calibrated probability of acceptance, a date, or a second meeting.

## 7. How do you handle missing information?

Missing hard fields block the edge and may trigger a bundled clarification.
Declined hard answers are not requested again. Missing soft fields add neither
credit nor penalty.

## 8. Why sort by member ID?

Opaque IDs are used only as a deterministic tie-break after arrival day or pair
score. They are never used to predict an outcome.

## 9. How do you handle delayed feedback?

The submitted method uses only events present in the current observable
request. Pending introductions remain blocked. We tested history-based scoring,
but its gain was uncertain, so it remains outside the submitted runtime.

## 10. Is 0.4444 a strong score?

It is the best score among our submitted public comparisons, but it is based on
three public seed groups. The paired interval against greedy starts at zero, so
we call the result promising rather than conclusive.

## 11. Why is the sparse score zero?

Sparse worlds produce very few feasible edges. Stable clarification alone does
not solve that supply problem. This is the clearest known weakness and the
first target for a larger, untouched experiment.

## 12. What would you improve next?

We would test scarcity-aware clarification and selective waiting on a larger
pre-registered seed block. We would promote a change only if it improves the
primary metric without violating constraints or losing the official
tie-breaks.

## 13. Does the policy make a fairness claim?

No. We report service by profile completeness and opportunity in the research
material, but the synthetic simulator does not justify a demographic fairness
or real-world dating claim.

## 14. How reproducible is the result?

The repository pins the submitted commit and container base, records result
hashes, checks the full seed-by-scenario matrix, and provides the commands used
to rebuild the summary. The policy is offline and deterministic.

## 15. What happens on malformed input?

The policy fails closed. It rejects future observations, conflicting duplicate
rows, invalid missing-value states, and other contract violations instead of
silently choosing one record.

## 16. What edge cases did you test?

The suite covers empty and odd pools, one-edge graphs, duplicate records,
declined answers, day-boundary feedback, repeated pairs, refreshed post-ask
state, replay, hash-seed changes, dense graphs, payload limits, and action
determinism.

## 17. What does the container prove?

It proves the submitted files run through the official JSON boundary within
the recorded public check. It does not prove a private score or real-world
performance.

## 18. Why should this team advance?

We turned evaluator feedback into a stricter scientific and release process.
The final method is understandable, constraint-safe, reproducible, and honest
about its failure cases. That gives the next round a dependable base for
targeted improvement.

## 19. Can you walk through one daily decision?

Use slide 5. D has one missing hard field, so the policy spends one bundled
clarification. It rebuilds the graph from the refreshed observation, ranks the
three reciprocal feasible edges, takes A-D first, skips A-B because A is now
used, and then takes the disjoint B-C edge. The example is fictional and shows
control flow, not a measured result.

## Questions to ask the organisers if invited

- Will the ten-minute limit include screen-sharing setup?
- May teams use backup slides during the five-minute Q&A?
- Will the judges have the repository open during the pitch?
- Should the final deck be submitted in advance or only screen-shared?
- Is a live demo expected, optional, or discouraged?
