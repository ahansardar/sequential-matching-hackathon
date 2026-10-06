"""Contract and allocation tests for the safe-cardinality policy."""
from __future__ import annotations

import json
import random
import unittest

from adaptive import _maximum_cardinality, _safe_batch, decide, plan_asks, select_pairs
from kit import Simulator, baseline_asks, baseline_match, eligibility, generate


class AdaptivePolicyTests(unittest.TestCase):
    def test_blossom_cardinality_matches_bruteforce_on_small_graphs(self):
        def brute(vertices, edge_set):
            if not vertices:
                return 0
            first = vertices[0]
            best = brute(vertices[1:], edge_set)
            for position, other in enumerate(vertices[1:]):
                if tuple(sorted((first, other))) in edge_set:
                    remaining = vertices[1:position + 1] + vertices[position + 2:]
                    best = max(best, 1 + brute(remaining, edge_set))
            return best

        generator = random.Random(17)
        for size in range(2, 9):
            vertices = [str(index) for index in range(size)]
            for _ in range(15):
                edges = {
                    (left, right): generator.random()
                    for left in vertices
                    for right in vertices
                    if left < right and generator.random() < 0.35
                }
                self.assertEqual(
                    len(_maximum_cardinality(edges)),
                    brute(vertices, set(edges)),
                )

    def test_blossom_allocator_finds_larger_batch_than_greedy_edge_order(self):
        edges = {
            ("a", "b"): 100.0,
            ("a", "c"): 5.0,
            ("b", "d"): 5.0,
        }
        self.assertEqual(_maximum_cardinality(edges), [("a", "c"), ("b", "d")])

    def test_safe_batch_requires_cardinality_and_quality_improvement(self):
        improving = {
            ("a", "b"): 6.0,
            ("a", "c"): 4.0,
            ("b", "d"): 4.0,
        }
        self.assertEqual(_safe_batch(improving), [("a", "c"), ("b", "d")])
        no_cardinality_gain = {("a", "b"): 6.0, ("a", "c"): 7.0}
        self.assertEqual(_safe_batch(no_cardinality_gain), [("a", "c")])

    def test_greedy_ablation_matches_supplied_baseline(self):
        simulator = Simulator(generate(3005, 80, "test", "development"))
        for _ in range(8):
            simulator.resolve_asks(baseline_asks(simulator.observe()))
            state = simulator.observe()
            pairs, _ = select_pairs(state, mode="adaptive_greedy")
            self.assertEqual([list(pair) for pair in pairs], baseline_match(state))
            simulator.advance([list(pair) for pair in pairs])

    def test_asks_match_supplied_policy_and_stay_within_budget(self):
        state = Simulator(generate(3001, 80, "test", "cold_start")).observe()
        first = plan_asks(state)
        self.assertEqual(first, baseline_asks(state))
        self.assertEqual(len({(row["member_id"], row["field"]) for row in first}), len(first))
        cost = sum(3 if row["field"] == "constraints" else 1 for row in first)
        self.assertLessEqual(cost, state["ask_budget_remaining"])

    def test_selected_pairs_are_valid_non_overlapping_and_deterministic(self):
        simulator = Simulator(generate(3002, 80, "test", "development"))
        memory = None
        for _ in range(8):
            ask_response = decide({"phase": "ask", "state": simulator.observe(), "memory": memory})
            simulator.resolve_asks(ask_response["asks"])
            match_state = simulator.observe()
            first = decide({"phase": "match", "state": match_state, "memory": ask_response["memory"]})
            second = decide({"phase": "match", "state": match_state, "memory": ask_response["memory"]})
            self.assertEqual(first, second)
            flattened = [member for pair in first["pairs"] for member in pair]
            self.assertEqual(len(flattened), len(set(flattened)))
            members = {member["member_id"]: member for member in match_state["members"]}
            for left, right in first["pairs"]:
                self.assertTrue(members[left]["available"])
                self.assertTrue(members[right]["available"])
                self.assertEqual(eligibility(members[left], members[right])["status"], "feasible")
            simulator.advance(first["pairs"])
            memory = first["memory"]

    def test_memory_is_small_finite_json(self):
        state = Simulator(generate(3003, 20, "test", "development")).observe()
        response = decide({"phase": "ask", "state": state, "memory": None})
        encoded = json.dumps(response["memory"], allow_nan=False).encode()
        self.assertLess(len(encoded), 1024 * 1024)

    def test_empty_state(self):
        state = {
            "day": 0,
            "ask_budget_remaining": 12,
            "members": [],
            "introductions": [],
            "feedback": [],
        }
        self.assertEqual(plan_asks(state), [])
        self.assertEqual(select_pairs(state)[0], [])


if __name__ == "__main__":
    unittest.main()
