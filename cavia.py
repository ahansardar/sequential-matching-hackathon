"""CAVIA-Match prototype using only observable policy inputs.

CAVIA stands for Constraint-Aware Value-of-Information Allocation.  The
prototype is deliberately dependency-free and deterministic so it remains easy
to audit inside the competition limits.
"""
from __future__ import annotations

import collections
import itertools
import math

from kit import HARD, SOFT, baseline_asks, baseline_match, eligibility


VERSION = "cavia-0.1"
SOFT_WEIGHTS = {
    "relationship_goal": 3.0,
    "relationship_pace": 2.0,
    "lifestyle": 1.0,
    "conversations": 1.0,
    "emotional_availability": 2.0,
    "space_for_relationship": 2.0,
    "relocate": 0.5,
}
TOTAL_SOFT_WEIGHT = sum(SOFT_WEIGHTS.values())


def _pair_key(a, b):
    return tuple(sorted((a, b)))


def _past_pairs(state):
    return {
        _pair_key(item["user_a"], item["user_b"])
        for item in state.get("introductions", [])
    }


def _available_members(state):
    return sorted(
        (member for member in state.get("members", []) if member.get("available")),
        key=lambda member: member["member_id"],
    )


def _field_at(member, field, day=None):
    value = member.get("fields", {}).get(field)
    if value is None or day is None:
        return value
    observed_day = member.get("field_observed_day", {}).get(field)
    if observed_day is None or observed_day > day:
        return None
    return value


def _soft_profile(a, b, day=None):
    matched_weight = 0.0
    missing_weight = 0.0
    observed_fields = 0
    matched_fields = 0
    for field, weight in SOFT_WEIGHTS.items():
        left = _field_at(a, field, day)
        right = _field_at(b, field, day)
        if left is None or right is None:
            missing_weight += weight
            continue
        observed_fields += 1
        if left == right:
            matched_fields += 1
            matched_weight += weight
    if observed_fields == 0:
        bucket = "unknown"
    elif matched_fields <= 1:
        bucket = "low"
    elif matched_fields <= 3:
        bucket = "medium"
    else:
        bucket = "high"
    return {
        "matched_weight": matched_weight,
        "missing_weight": missing_weight,
        "bucket": bucket,
    }


def _potential_edges(state):
    """Return non-infeasible edges without treating missing data as permission."""
    members = _available_members(state)
    past = _past_pairs(state)
    edges = []
    for left, right in itertools.combinations(members, 2):
        key = _pair_key(left["member_id"], right["member_id"])
        if key in past:
            continue
        status = eligibility(left, right)
        if status["status"] == "infeasible":
            continue
        edges.append((left, right, status))
    return edges


def targeted_asks(state):
    """Rank hard-bundle asks by an observable value-of-information proxy."""
    budget = max(0, int(state.get("ask_budget_remaining", 0)))
    capacity = budget // 3
    if capacity == 0:
        return []

    members = _available_members(state)
    potential_degree = collections.Counter()
    feasible_degree = collections.Counter()
    priority = collections.defaultdict(float)

    for left, right, status in _potential_edges(state):
        left_id = left["member_id"]
        right_id = right["member_id"]
        potential_degree[left_id] += 1
        potential_degree[right_id] += 1
        if status["status"] == "feasible":
            feasible_degree[left_id] += 1
            feasible_degree[right_id] += 1
            continue

        missing_owners = {item.split(":", 1)[0] for item in status.get("missing", [])}
        profile = _soft_profile(left, right)
        quality = 1.0 + profile["matched_weight"] / TOTAL_SOFT_WEIGHT
        for member_id in (left_id, right_id):
            if member_id not in missing_owners:
                continue
            # Fully resolvable edges are more valuable than edges that still need
            # information from the other endpoint.
            factor = 2.0 if missing_owners == {member_id} else 0.6
            priority[member_id] += quality * factor

    ranked = []
    day = int(state.get("day", 0))
    for member in members:
        member_id = member["member_id"]
        statuses = member.get("field_status", {})
        missing = [field for field in HARD if member.get("fields", {}).get(field) is None]
        if not missing or any(statuses.get(field) == "declined" for field in missing):
            continue
        if not any(statuses.get(field) == "not_asked" for field in missing):
            continue

        score = priority[member_id]
        if potential_degree[member_id] and not feasible_degree[member_id]:
            score += 2.0
        score += 1.0 / (1.0 + potential_degree[member_id])
        score += min(30, max(0, day - int(member.get("arrived_day", day)))) * 0.01
        ranked.append((-score, member_id))

    ranked.sort()
    return [
        {"member_id": member_id, "field": "constraints"}
        for _, member_id in ranked[:capacity]
    ]


def _feedback_statistics(state):
    """Build recency-weighted operational outcome statistics.

    A missing response counts only as absence of the explicitly modelled
    recorded-Yes event.  It is never interpreted as dislike or rejection.
    """
    day = int(state.get("day", 0))
    members = {member["member_id"]: member for member in state.get("members", [])}
    events = collections.defaultdict(list)
    for event in state.get("feedback", []):
        events[event["introduction_id"]].append(event)

    stats = {
        "mutual": collections.defaultdict(lambda: [0.0, 0.0]),
        "msmi": collections.defaultdict(lambda: [0.0, 0.0]),
        "matured_mutual": 0,
        "matured_msmi": 0,
    }
    for intro in state.get("introductions", []):
        left = members.get(intro["user_a"])
        right = members.get(intro["user_b"])
        if left is None or right is None:
            continue
        assigned = int(intro["assigned_day"])
        bucket = _soft_profile(left, right, assigned)["bucket"]
        age = max(0, day - assigned)
        recency_weight = math.pow(0.5, age / 30.0)
        observed = events.get(intro["introduction_id"], [])

        if age >= 7:
            responses = [e for e in observed if e.get("event") == "introduction_response"]
            success = len(responses) == 2 and all(e.get("value") == "yes" for e in responses)
            stats["mutual"][bucket][0 if success else 1] += recency_weight
            stats["matured_mutual"] += 1

        # The public simulator's longest delayed path is 38 days.  Waiting this
        # long avoids turning a still-developing outcome into a negative label.
        if age >= 38:
            dates = [
                e for e in observed
                if e.get("event") == "date_happened"
                and e.get("value") is True
                and e.get("occurred_day", assigned + 31) - assigned <= 30
            ]
            seconds = [e for e in observed if e.get("event") == "second_meeting_intention"]
            success = bool(dates) and len(seconds) == 2 and all(
                e.get("value") == "yes"
                and e.get("occurred_day", dates[0]["occurred_day"] + 4)
                - dates[0]["occurred_day"] <= 3
                for e in seconds
            )
            stats["msmi"][bucket][0 if success else 1] += recency_weight
            stats["matured_msmi"] += 1
    return stats


def _posterior(stats, outcome, bucket, prior_success, prior_failure):
    success, failure = stats[outcome][bucket]
    return (prior_success + success) / (prior_success + prior_failure + success + failure)


def scored_edges(state, use_uncertainty=True, use_feedback=True):
    members = _available_members(state)
    past = _past_pairs(state)
    stats = _feedback_statistics(state)
    raw = []
    degree = collections.Counter()

    for left, right in itertools.combinations(members, 2):
        key = _pair_key(left["member_id"], right["member_id"])
        if key in past or eligibility(left, right)["status"] != "feasible":
            continue
        degree[left["member_id"]] += 1
        degree[right["member_id"]] += 1
        raw.append((left, right, key))

    day = int(state.get("day", 0))
    edges = {}
    for left, right, key in raw:
        profile = _soft_profile(left, right)
        compatibility = 4.0 * profile["matched_weight"] / TOTAL_SOFT_WEIGHT
        uncertainty = 1.5 * profile["missing_weight"] / TOTAL_SOFT_WEIGHT if use_uncertainty else 0.0
        scarcity = 0.75 * (
            1.0 / max(1, degree[left["member_id"]])
            + 1.0 / max(1, degree[right["member_id"]])
        )
        waiting = 0.015 * min(
            60,
            max(0, day - int(left.get("arrived_day", day)))
            + max(0, day - int(right.get("arrived_day", day))),
        )
        feedback = 0.0
        if use_feedback:
            mutual = _posterior(stats, "mutual", profile["bucket"], 1.0, 1.0)
            msmi = _posterior(stats, "msmi", profile["bucket"], 0.5, 9.5)
            feedback = 1.5 * mutual + 6.0 * msmi
        edges[key] = 1.0 + compatibility + scarcity + waiting + feedback - uncertainty
    return edges, stats


def greedy_allocation(edges):
    selected = []
    used = set()
    for pair, _ in sorted(edges.items(), key=lambda item: (-item[1], item[0])):
        if not used.intersection(pair):
            selected.append(pair)
            used.update(pair)
    return sorted(selected)


def improved_allocation(edges, max_exchanges=12):
    """Greedy matching followed by deterministic best two-edge exchanges."""
    selected = set(greedy_allocation(edges))
    for _ in range(max_exchanges):
        ordered = sorted(selected)
        best = None
        for index, first in enumerate(ordered):
            for second in ordered[index + 1:]:
                a, b = first
                c, d = second
                old_score = edges[first] + edges[second]
                alternatives = (
                    (_pair_key(a, c), _pair_key(b, d)),
                    (_pair_key(a, d), _pair_key(b, c)),
                )
                for replacement in alternatives:
                    if replacement[0] not in edges or replacement[1] not in edges:
                        continue
                    if replacement[0] == replacement[1]:
                        continue
                    gain = edges[replacement[0]] + edges[replacement[1]] - old_score
                    candidate = (gain, tuple(sorted(replacement)), first, second)
                    if gain > 1e-12 and (best is None or candidate[0] > best[0] + 1e-12
                                         or (abs(candidate[0] - best[0]) <= 1e-12
                                             and candidate[1] < best[1])):
                        best = candidate
        if best is None:
            break
        _, replacement, first, second = best
        selected.remove(first)
        selected.remove(second)
        selected.update(replacement)
    return sorted(selected)


def decide(request, mode="cavia"):
    state = request["state"]
    memory = request.get("memory") or {}
    if request["phase"] == "ask":
        asks = baseline_asks(state) if mode == "cavia_no_targeted_asks" else targeted_asks(state)
        next_memory = dict(memory)
        next_memory.update({"policy": VERSION, "day": state.get("day", 0)})
        return {"asks": asks, "memory": next_memory}

    use_uncertainty = mode != "cavia_no_uncertainty"
    use_feedback = mode != "cavia_no_feedback"
    edges, stats = scored_edges(state, use_uncertainty=use_uncertainty, use_feedback=use_feedback)
    if mode == "cavia_targeted_baseline":
        pairs = [tuple(pair) for pair in baseline_match(state)]
    else:
        pairs = greedy_allocation(edges) if mode == "cavia_greedy" else improved_allocation(edges)
    next_memory = {
        "policy": VERSION,
        "day": state.get("day", 0),
        "matured_mutual": stats["matured_mutual"],
        "matured_msmi": stats["matured_msmi"],
    }
    return {"pairs": [list(pair) for pair in pairs], "memory": next_memory}
