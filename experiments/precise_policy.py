"""Rejected objective-separation challengers kept for reproducible research."""
from __future__ import annotations

from adaptive import (
    ACCEPT_PRIOR,
    HISTORY_START_DAY,
    RESPONSE_PRIOR,
    VERSION,
    _compatibility_edges,
    _feedback_history,
    _greedy_pairs,
    _logit,
    _maximum_cardinality,
    _maximum_quality_batch,
    _pair_key,
    _posterior,
    _scored_edges,
    plan_asks,
)


HISTORY_SIGNAL_LIMIT = 3.0


def _confidence_weighted_history_signal(history):
    history = history or {}
    response = _posterior(
        history.get("responses", 0),
        history.get("response_trials", 0),
        RESPONSE_PRIOR,
    )
    acceptance = _posterior(
        history.get("accepts", 0),
        history.get("accept_trials", 0),
        ACCEPT_PRIOR,
    )
    signal = (
        _logit(response)
        - _logit(RESPONSE_PRIOR[0])
        + _logit(acceptance)
        - _logit(ACCEPT_PRIOR[0])
    )
    return max(-HISTORY_SIGNAL_LIMIT, min(HISTORY_SIGNAL_LIMIT, signal))


def _precise_edge_objectives(state):
    compatibility = _compatibility_edges(state)
    if state.get("day", 0) < HISTORY_START_DAY:
        return compatibility, {pair: 0.0 for pair in compatibility}
    histories = _feedback_history(state)
    signals = {
        member_id: _confidence_weighted_history_signal(histories.get(member_id))
        for pair in compatibility
        for member_id in pair
    }
    history = {
        pair: signals[pair[0]] + signals[pair[1]]
        for pair in compatibility
    }
    return compatibility, history


def _raw_compatibility_guarded_batch(compatibility, scored):
    greedy = _greedy_pairs(scored)
    maximum = _maximum_quality_batch(scored)
    if (
        len(maximum) > len(greedy)
        and sum(compatibility[pair] for pair in maximum) + 1e-12
        >= sum(compatibility[pair] for pair in greedy)
    ):
        return maximum
    return greedy


def _greedy_pairs_lexicographic(compatibility, history):
    selected = []
    used = set()
    ordered = sorted(
        compatibility,
        key=lambda pair: (-compatibility[pair], -history[pair], pair),
    )
    for pair in ordered:
        if not used.intersection(pair):
            selected.append(pair)
            used.update(pair)
    return selected


def _batch_objective(pairs, compatibility, history):
    return (
        sum(compatibility[pair] for pair in pairs),
        sum(history[pair] for pair in pairs),
    )


def _refine_lexicographic(selected, compatibility, history, max_rounds=20):
    chosen = set(selected)
    all_members = {member for pair in compatibility for member in pair}
    for _ in range(max_rounds):
        used = {member for pair in chosen for member in pair}
        unmatched = sorted(all_members - used)
        current = _batch_objective(chosen, compatibility, history)
        best = None
        ordered = sorted(chosen)

        def consider(replacements, removed):
            nonlocal best
            candidate_pairs = chosen.difference(removed).union(replacements)
            objective = _batch_objective(candidate_pairs, compatibility, history)
            if objective <= current:
                return
            candidate = (objective, tuple(sorted(replacements)), tuple(sorted(removed)))
            if best is None or candidate > best:
                best = candidate

        for old in ordered:
            left, right = old
            for free in unmatched:
                for replacement in (_pair_key(left, free), _pair_key(right, free)):
                    if replacement in compatibility:
                        consider((replacement,), (old,))

        for position, first in enumerate(ordered):
            for second in ordered[position + 1:]:
                a, b = first
                c, d = second
                for replacements in (
                    (_pair_key(a, c), _pair_key(b, d)),
                    (_pair_key(a, d), _pair_key(b, c)),
                ):
                    if (
                        replacements[0] != replacements[1]
                        and all(pair in compatibility for pair in replacements)
                    ):
                        consider(replacements, (first, second))

        if best is None:
            break
        _, replacements, removed = best
        chosen.difference_update(removed)
        chosen.update(replacements)
    return sorted(chosen)


def _precise_batch(compatibility, history):
    greedy = _greedy_pairs_lexicographic(compatibility, history)
    ranked = {
        pair: 100.0 * compatibility[pair] + history[pair]
        for pair in compatibility
    }
    maximum = _refine_lexicographic(
        _maximum_cardinality(ranked),
        compatibility,
        history,
    )
    greedy_compatibility, _ = _batch_objective(greedy, compatibility, history)
    maximum_compatibility, _ = _batch_objective(maximum, compatibility, history)
    if (
        len(maximum) > len(greedy)
        and maximum_compatibility + 1e-12 >= greedy_compatibility
    ):
        return maximum
    return greedy


def select_pairs(state, mode):
    compatibility = _compatibility_edges(state)
    if mode == "adaptive_raw_guard":
        scored = _scored_edges(state)
        return _raw_compatibility_guarded_batch(compatibility, scored), scored
    compatibility, history = _precise_edge_objectives(state)
    return _precise_batch(compatibility, history), compatibility


def decide(request, mode):
    state = request["state"]
    memory = request.get("memory") or {}
    if request["phase"] == "ask":
        return {
            "asks": plan_asks(state),
            "memory": {"policy": VERSION, "day": state.get("day", 0)},
        }
    pairs, edges = select_pairs(state, mode)
    next_memory = dict(memory)
    next_memory.update({
        "policy": VERSION,
        "day": state.get("day", 0),
        "candidate_edges": len(edges),
    })
    return {"pairs": [list(pair) for pair in pairs], "memory": next_memory}
