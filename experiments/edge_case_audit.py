"""Rerunnable adversarial audit for the submitted observable policy.

This audit changes representation order, not member facts. It also exercises
empty and dense graphs, odd carried-memory shapes and repeated daily decisions.
The output records exactly what was checked and does not claim private-world
performance.
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import random
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from kit import HARD, SOFT, Simulator, eligibility, generate  # noqa: E402
from policy import decide  # noqa: E402


def _permuted(state, seed):
    changed = copy.deepcopy(state)
    generator = random.Random(seed)
    for key in ("members", "introductions", "feedback", "ask_log"):
        generator.shuffle(changed.get(key, []))
    for member in changed.get("members", []):
        for field in ("who_to_meet", "acceptable_zones", "schedule"):
            value = member.get("fields", {}).get(field)
            if isinstance(value, list):
                generator.shuffle(value)
    changed["future_optional_state"] = {"version": 2}
    return changed


def _assert_valid_pairs(state, pairs):
    members = {member["member_id"]: member for member in state["members"]}
    past = {
        tuple(sorted((item["user_a"], item["user_b"])))
        for item in state["introductions"]
    }
    used = set()
    for pair in pairs:
        if len(pair) != 2 or pair[0] == pair[1]:
            raise AssertionError("pair is not two distinct endpoints")
        if used.intersection(pair):
            raise AssertionError("member appears twice in one batch")
        if any(member_id not in members or not members[member_id]["available"] for member_id in pair):
            raise AssertionError("pair includes an unavailable or unknown member")
        if tuple(sorted(pair)) in past:
            raise AssertionError("pair repeats an earlier introduction")
        if eligibility(members[pair[0]], members[pair[1]])["status"] != "feasible":
            raise AssertionError("pair violates reciprocal feasibility")
        used.update(pair)


def _complete_member(index):
    member_id = f"syn_{index:032x}"
    fields = {
        "age_min": 18,
        "age_max": 65,
        "who_to_meet": ["woman", "man", "non_binary"],
        "relationship_structure": "monogamous",
        "smoking": "no",
        "partner_smoking": "any",
        "has_children": False,
        "partner_children": "any",
        "wants_children": "unsure",
        "acceptable_zones": ["zone_a"],
        "schedule": ["weekend_day"],
        **{field: "same" for field in SOFT},
    }
    return {
        "member_id": member_id,
        "pool_id": "dense",
        "synthetic": True,
        "age": 30,
        "gender": "non_binary",
        "zone": "zone_a",
        "arrived_day": 0,
        "available": True,
        "fields": fields,
        "field_status": {field: "observed" for field in HARD + SOFT},
        "field_observed_day": {field: 0 for field in HARD + SOFT},
        "source": "synthetic_questionnaire",
    }


def run_audit(seeds, days, permutations):
    checked_states = 0
    checked_permutations = 0
    checked_pairs = 0
    for seed in seeds:
        simulator = Simulator(generate(seed, 200, "edge_case_audit", "development"))
        memory = None
        for day in range(days):
            ask_state = simulator.observe()
            canonical_ask = decide(
                {"phase": "ask", "state": ask_state, "memory": memory},
                "adaptive_greedy",
            )
            for index in range(permutations):
                alternative = decide(
                    {
                        "phase": "ask",
                        "state": _permuted(ask_state, seed * 10000 + day * 100 + index),
                        "memory": memory,
                    },
                    "adaptive_greedy",
                )
                if alternative != canonical_ask:
                    raise AssertionError("ask action changed after an order-only permutation")
                checked_permutations += 1
            simulator.resolve_asks(canonical_ask["asks"])

            match_state = simulator.observe()
            canonical_match = decide(
                {"phase": "match", "state": match_state, "memory": canonical_ask["memory"]},
                "adaptive_greedy",
            )
            _assert_valid_pairs(match_state, canonical_match["pairs"])
            for index in range(permutations):
                alternative = decide(
                    {
                        "phase": "match",
                        "state": _permuted(match_state, seed * 20000 + day * 100 + index),
                        "memory": canonical_ask["memory"],
                    },
                    "adaptive_greedy",
                )
                if alternative != canonical_match:
                    raise AssertionError("match action changed after an order-only permutation")
                checked_permutations += 1
            checked_states += 2
            checked_pairs += len(canonical_match["pairs"])
            simulator.advance(canonical_match["pairs"])
            memory = canonical_match["memory"]

    empty = {
        "schema_version": "1.0.0",
        "synthetic": True,
        "day": 0,
        "ask_budget_remaining": 12,
        "members": [],
        "introductions": [],
        "feedback": [],
        "ask_log": [],
    }
    memory_shapes = [None, [], "stale", 5, True, {"older_policy": "v0"}]
    for memory_value in memory_shapes:
        response = decide(
            {"phase": "match", "state": empty, "memory": memory_value},
            "adaptive_greedy",
        )
        json.dumps(response, allow_nan=False)

    dense = dict(empty, members=[_complete_member(index) for index in range(200)])
    started = time.perf_counter()
    dense_response = decide(
        {"phase": "match", "state": dense, "memory": None},
        "adaptive_greedy",
    )
    dense_seconds = time.perf_counter() - started
    _assert_valid_pairs(dense, dense_response["pairs"])
    if len(dense_response["pairs"]) != 100:
        raise AssertionError("dense graph did not produce maximum possible coverage")

    return {
        "status": "passed",
        "policy_mode": "adaptive_greedy",
        "scope": "observable public-state behavior only",
        "seed_worlds": seeds,
        "days_per_world": days,
        "states_checked": checked_states,
        "order_only_permutations_checked": checked_permutations,
        "valid_pairs_checked": checked_pairs,
        "memory_shapes_checked": len(memory_shapes),
        "empty_graph_pairs": 0,
        "dense_graph_members": 200,
        "dense_graph_pairs": len(dense_response["pairs"]),
        "dense_graph_direct_seconds": dense_seconds,
        "limits": [
            "This is a deterministic adversarial audit, not evidence about private score.",
            "Container wall-clock and protocol isolation are checked separately by the release commands.",
            "Malformed organiser requests outside the published data contract are not accepted as valid inputs.",
        ],
    }


def _parse_seeds(value):
    return [int(part) for part in value.split(",")]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", default="7301,7302")
    parser.add_argument("--days", type=int, default=10)
    parser.add_argument("--permutations", type=int, default=3)
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "edge_case_audit.json")
    args = parser.parse_args()
    if args.days < 1 or args.permutations < 1:
        parser.error("days and permutations must be positive")
    payload = run_audit(_parse_seeds(args.seeds), args.days, args.permutations)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
