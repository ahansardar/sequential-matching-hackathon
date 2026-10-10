"""Contract and allocation tests for the safe-cardinality policy."""
from __future__ import annotations

import json
import random
import unittest

from adaptive import (
    HISTORY_MEMBER_LIMIT,
    _feedback_history,
    _history_quality,
    _maximum_cardinality,
    _graph_aware_asks,
    _safe_batch,
    _scored_edges,
    decide,
    plan_asks,
    select_pairs,
)
from kit import HARD, SOFT, Simulator, baseline_asks, baseline_match, eligibility, generate


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

    def test_graph_aware_asks_prioritise_a_one_step_unlock(self):
        known_fields = {
            "age_min": 18, "age_max": 40, "who_to_meet": ["woman"],
            "relationship_structure": "monogamous", "smoking": "no",
            "partner_smoking": "any", "has_children": False,
            "partner_children": "any", "wants_children": "unsure",
            "acceptable_zones": ["zone_a"], "schedule": ["weekend_day"],
            **{field: None for field in SOFT},
        }

        def missing(member_id, gender):
            return {
                "member_id": member_id, "pool_id": "test", "age": 25,
                "gender": gender, "zone": "zone_a", "available": True,
                "fields": {**{field: None for field in HARD},
                           **{field: None for field in SOFT}},
                "field_status": {field: "not_asked" for field in HARD + SOFT},
            }

        known = {
            "member_id": "known", "pool_id": "test", "age": 25,
            "gender": "man", "zone": "zone_a", "available": True,
            "fields": known_fields,
            "field_status": {field: "observed" for field in HARD + SOFT},
        }
        blocked_first = missing("blocked", "man")
        unlock_second = missing("unlock", "woman")
        state = {
            "ask_budget_remaining": 3,
            "members": [blocked_first, unlock_second, known],
        }
        self.assertEqual(
            _graph_aware_asks(state),
            [{"member_id": "unlock", "field": "constraints"}],
        )

    def test_graph_aware_asks_handle_small_budget_declines_and_ties(self):
        def incomplete(member_id, status="not_asked"):
            return {
                "member_id": member_id,
                "available": True,
                "fields": {field: None for field in HARD},
                "field_status": {field: status for field in HARD},
            }

        tied_first = incomplete("first")
        tied_second = incomplete("second")
        declined = incomplete("declined", status="declined")
        state = {
            "ask_budget_remaining": 2,
            "members": [declined, tied_first, tied_second],
        }
        self.assertEqual(_graph_aware_asks(state), [])
        state["ask_budget_remaining"] = 6
        self.assertEqual(
            _graph_aware_asks(state),
            [
                {"member_id": "first", "field": "constraints"},
                {"member_id": "second", "field": "constraints"},
            ],
        )

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

    def test_history_uses_only_observed_directional_responses(self):
        state = {
            "feedback": [
                {"event": "introduction_response", "member_id": "a", "value": "yes"},
                {"event": "introduction_response", "member_id": "a", "value": None},
                {"event": "introduction_response", "member_id": "b", "value": "no"},
                {"event": "date_happened", "member_id": None, "value": True},
            ]
        }
        histories = _feedback_history(state)
        self.assertEqual(
            histories["a"],
            {"response_trials": 2, "responses": 1, "accept_trials": 1, "accepts": 1},
        )
        self.assertEqual(
            histories["b"],
            {"response_trials": 1, "responses": 1, "accept_trials": 1, "accepts": 0},
        )
        self.assertGreater(_history_quality(histories["a"]), _history_quality(histories["b"]))

    def test_history_quality_is_explicitly_bounded(self):
        positive = _history_quality({
            "response_trials": 1_000_000,
            "responses": 1_000_000,
            "accept_trials": 1_000_000,
            "accepts": 1_000_000,
        })
        negative = _history_quality({
            "response_trials": 1_000_000,
            "responses": 0,
            "accept_trials": 1_000_000,
            "accepts": 0,
        })
        self.assertEqual(positive, HISTORY_MEMBER_LIMIT)
        self.assertEqual(negative, -HISTORY_MEMBER_LIMIT)

    def test_history_signal_starts_on_day_twenty(self):
        fields = {
            "age_min": 18,
            "age_max": 40,
            "who_to_meet": ["woman", "man"],
            "relationship_structure": "monogamous",
            "smoking": "no",
            "partner_smoking": "no_smoking",
            "has_children": False,
            "partner_children": "no_children",
            "wants_children": "yes",
            "acceptable_zones": ["central"],
            "schedule": ["weekend_day"],
            "relationship_goal": "long_term",
            "relationship_pace": "steady",
            "lifestyle": "balanced",
            "conversations": "deep",
            "emotional_availability": "ready",
            "space_for_relationship": "ample",
            "relocate": "yes",
        }

        def member(member_id, gender):
            return {
                "member_id": member_id,
                "pool_id": "test",
                "age": 25,
                "gender": gender,
                "zone": "central",
                "available": True,
                "fields": dict(fields),
            }

        state = {
            "day": 19,
            "members": [member("a", "woman"), member("b", "man")],
            "introductions": [],
            "feedback": [
                {"event": "introduction_response", "member_id": "a", "value": "yes"},
                {"event": "introduction_response", "member_id": "b", "value": "no"},
            ],
        }
        early = _scored_edges(state)[("a", "b")]
        state["day"] = 20
        mature = _scored_edges(state)[("a", "b")]
        self.assertEqual(early, 700.0)
        self.assertNotEqual(mature, early)

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
