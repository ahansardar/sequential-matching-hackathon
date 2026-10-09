"""Guarded-history policy for sequential reciprocal matching.

The policy keeps the supplied clarification and reciprocal feasibility rules.
It ranks feasible pairs by observed compatibility, then adds a small mature-
history signal from day 20. Inference uses only the observable JSON request.
"""
from __future__ import annotations

import collections
import itertools
import math

from kit import HARD, SOFT, baseline_asks, eligibility


VERSION = "guarded-history-2.1"
HISTORY_START_DAY = 20
RESPONSE_PRIOR = (0.765, 4.0)
ACCEPT_PRIOR = (0.46, 4.0)
HISTORY_MEMBER_LIMIT = 20.0


def _pair_key(left, right):
    return tuple(sorted((left, right)))


def _available_with_known_constraints(state):
    return sorted(
        (
            member for member in state.get("members", [])
            if member.get("available")
            and all(member.get("fields", {}).get(field) is not None for field in HARD)
        ),
        key=lambda member: member["member_id"],
    )


def _feedback_history(state):
    histories = {}

    def member_history(member_id):
        return histories.setdefault(member_id, {
            "response_trials": 0,
            "responses": 0,
            "accept_trials": 0,
            "accepts": 0,
        })

    for event in state.get("feedback", []):
        if event.get("event") != "introduction_response" or not event.get("member_id"):
            continue
        history = member_history(event["member_id"])
        history["response_trials"] += 1
        if event.get("value") is not None:
            history["responses"] += 1
            history["accept_trials"] += 1
            history["accepts"] += int(event.get("value") == "yes")
    return histories


def _posterior(successes, trials, prior):
    mean, strength = prior
    return (successes + mean * strength) / (trials + strength)


def _logit(value):
    value = min(1 - 1e-6, max(1e-6, value))
    return math.log(value / (1 - value))


def _history_quality(history):
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
    quality = _logit(response) + _logit(acceptance)
    return max(-HISTORY_MEMBER_LIMIT, min(HISTORY_MEMBER_LIMIT, quality))


def _compatibility_edges(state):
    members = _available_with_known_constraints(state)
    past = {
        _pair_key(item["user_a"], item["user_b"])
        for item in state.get("introductions", [])
    }
    edges = {}
    for left, right in itertools.combinations(members, 2):
        pair = _pair_key(left["member_id"], right["member_id"])
        if pair in past or eligibility(left, right)["status"] != "feasible":
            continue
        fields_left = left.get("fields", {})
        fields_right = right.get("fields", {})
        edges[pair] = float(sum(
            fields_left.get(field) is not None
            and fields_left.get(field) == fields_right.get(field)
            for field in SOFT
        ))
    return edges


def _scored_edges(state):
    """Keep compatibility primary and use mature feedback as a tie-breaker."""
    compatibility = _compatibility_edges(state)
    if state.get("day", 0) < HISTORY_START_DAY:
        return {pair: 100.0 * score for pair, score in compatibility.items()}
    histories = _feedback_history(state)
    quality = {
        member_id: _history_quality(histories.get(member_id))
        for pair in compatibility
        for member_id in pair
    }
    return {
        pair: 100.0 * score + quality[pair[0]] + quality[pair[1]]
        for pair, score in compatibility.items()
    }


def _greedy_pairs(edges):
    selected = []
    used = set()
    for pair, _ in sorted(edges.items(), key=lambda item: (-item[1], item[0])):
        if not used.intersection(pair):
            selected.append(pair)
            used.update(pair)
    return selected


def _maximum_cardinality(edges):
    """Return a deterministic maximum-cardinality general-graph matching."""
    if not edges:
        return []
    vertices = sorted({member for pair in edges for member in pair})
    index = {member: position for position, member in enumerate(vertices)}
    graph = [[] for _ in vertices]
    for left, right in edges:
        a, b = index[left], index[right]
        graph[a].append(b)
        graph[b].append(a)
    for vertex, neighbors in enumerate(graph):
        neighbors.sort(
            key=lambda other: (
                -edges[_pair_key(vertices[vertex], vertices[other])],
                vertices[other],
            )
        )

    size = len(vertices)
    match = [-1] * size
    parent = [-1] * size
    base = list(range(size))
    used = [False] * size
    blossom = [False] * size

    def lowest_common_ancestor(a, b):
        seen = [False] * size
        while True:
            a = base[a]
            seen[a] = True
            if match[a] == -1:
                break
            a = parent[match[a]]
        while True:
            b = base[b]
            if seen[b]:
                return b
            b = parent[match[b]]

    def mark_path(vertex, root, child):
        while base[vertex] != root:
            blossom[base[vertex]] = True
            blossom[base[match[vertex]]] = True
            parent[vertex] = child
            child = match[vertex]
            vertex = parent[match[vertex]]

    def find_path(root):
        for position in range(size):
            used[position] = False
            parent[position] = -1
            base[position] = position
        queue = collections.deque([root])
        used[root] = True
        while queue:
            vertex = queue.popleft()
            for other in graph[vertex]:
                if base[vertex] == base[other] or match[vertex] == other:
                    continue
                if other == root or (
                    match[other] != -1 and parent[match[other]] != -1
                ):
                    common = lowest_common_ancestor(vertex, other)
                    for position in range(size):
                        blossom[position] = False
                    mark_path(vertex, common, other)
                    mark_path(other, common, vertex)
                    for position in range(size):
                        if blossom[base[position]]:
                            base[position] = common
                            if not used[position]:
                                used[position] = True
                                queue.append(position)
                elif parent[other] == -1:
                    parent[other] = vertex
                    if match[other] == -1:
                        current = other
                        while current != -1:
                            previous = parent[current]
                            next_current = match[previous] if previous != -1 else -1
                            match[current] = previous
                            if previous != -1:
                                match[previous] = current
                            current = next_current
                        return True
                    other = match[other]
                    used[other] = True
                    queue.append(other)
        return False

    roots = sorted(range(size), key=lambda item: (-len(graph[item]), vertices[item]))
    for root in roots:
        if match[root] == -1:
            find_path(root)
    return sorted(
        _pair_key(vertices[position], vertices[partner])
        for position, partner in enumerate(match)
        if partner != -1 and position < partner
    )


def _refine_quality(selected, edges, max_rounds=20):
    """Improve observed compatibility without reducing batch cardinality."""
    chosen = set(selected)
    all_members = {member for pair in edges for member in pair}
    for _ in range(max_rounds):
        used = {member for pair in chosen for member in pair}
        unmatched = sorted(all_members - used)
        best = None
        ordered = sorted(chosen)

        for old in ordered:
            left, right = old
            for free in unmatched:
                for replacement in (_pair_key(left, free), _pair_key(right, free)):
                    if replacement not in edges:
                        continue
                    gain = edges[replacement] - edges[old]
                    candidate = (gain, (replacement,), (old,))
                    if gain > 1e-12 and (best is None or candidate > best):
                        best = candidate

        for position, first in enumerate(ordered):
            for second in ordered[position + 1:]:
                a, b = first
                c, d = second
                for replacements in (
                    (_pair_key(a, c), _pair_key(b, d)),
                    (_pair_key(a, d), _pair_key(b, c)),
                ):
                    if (
                        replacements[0] == replacements[1]
                        or any(pair not in edges for pair in replacements)
                    ):
                        continue
                    gain = (
                        sum(edges[pair] for pair in replacements)
                        - edges[first]
                        - edges[second]
                    )
                    candidate = (gain, tuple(sorted(replacements)), (first, second))
                    if gain > 1e-12 and (best is None or candidate > best):
                        best = candidate
        if best is None:
            break
        _, replacements, removed = best
        chosen.difference_update(removed)
        chosen.update(replacements)
    return sorted(chosen)


def _maximum_quality_batch(edges):
    return _refine_quality(_maximum_cardinality(edges), edges)


def _safe_batch(edges):
    """Accept global allocation only when it improves two observable measures."""
    greedy = _greedy_pairs(edges)
    maximum = _maximum_quality_batch(edges)
    if (
        len(maximum) > len(greedy)
        and sum(edges[pair] for pair in maximum) + 1e-12
        >= sum(edges[pair] for pair in greedy)
    ):
        return maximum
    return greedy


def select_pairs(state, mode="adaptive"):
    compatibility = _compatibility_edges(state)
    if mode == "adaptive_greedy":
        edges = compatibility
        pairs = _greedy_pairs(compatibility)
    elif mode == "adaptive_always_max":
        edges = compatibility
        pairs = _maximum_quality_batch(compatibility)
    elif mode == "adaptive_legacy":
        edges = compatibility
        pairs = _safe_batch(compatibility)
    else:
        edges = _scored_edges(state)
        pairs = _safe_batch(edges)
    return pairs, edges


def plan_asks(state):
    return baseline_asks(state)


def decide(request, mode="adaptive"):
    state = request["state"]
    memory = request.get("memory") or {}
    if request["phase"] == "ask":
        return {
            "asks": plan_asks(state),
            "memory": {"policy": VERSION, "day": state.get("day", 0)},
        }

    pairs, edges = select_pairs(state, mode=mode)
    next_memory = dict(memory)
    next_memory.update({
        "policy": VERSION,
        "day": state.get("day", 0),
        "candidate_edges": len(edges),
    })
    return {"pairs": [list(pair) for pair in pairs], "memory": next_memory}
