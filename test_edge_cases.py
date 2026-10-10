"""Adversarial boundary tests for the submitted policy and evidence rules."""
from __future__ import annotations

import copy
import json
import os
import random
import subprocess
import sys
import time
import unittest

from adaptive import decide, plan_asks
from evaluate import invoke
from experiments.outcome_events import (
    classify_funnel,
    recorded_yes_by_deadline,
    validate_event_sequence,
)
from kit import HARD, SOFT, eligibility


def complete_member(member_id, gender="woman", arrived_day=0):
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
        "relationship_goal": "long_term",
        "relationship_pace": "steady",
        "lifestyle": "quiet",
        "conversations": "ideas",
        "emotional_availability": "ready",
        "space_for_relationship": "ample",
        "relocate": "unsure",
    }
    return {
        "member_id": member_id,
        "pool_id": "edge",
        "synthetic": True,
        "age": 30,
        "gender": gender,
        "zone": "zone_a",
        "arrived_day": arrived_day,
        "available": True,
        "fields": fields,
        "field_status": {field: "observed" for field in HARD + SOFT},
        "field_observed_day": {field: arrived_day for field in HARD + SOFT},
        "source": "synthetic_questionnaire",
    }


def state(members, budget=12):
    return {
        "schema_version": "1.0.0",
        "synthetic": True,
        "day": 0,
        "ask_budget_remaining": budget,
        "members": members,
        "introductions": [],
        "feedback": [],
        "ask_log": [],
    }


class EdgeCaseTests(unittest.TestCase):
    def test_member_permutation_cannot_change_default_actions(self):
        members = [complete_member(f"m{index:03d}") for index in range(8)]
        for index, member in enumerate(members[:6]):
            member["fields"][HARD[index]] = None
            member["field_status"][HARD[index]] = "not_asked"
            member["field_observed_day"][HARD[index]] = None
        forward = state(members)
        reversed_state = state(list(reversed(copy.deepcopy(members))))
        self.assertEqual(plan_asks(forward, "adaptive_greedy"), plan_asks(reversed_state, "adaptive_greedy"))

        complete = state([complete_member(f"m{index:03d}") for index in range(12)])
        permuted = state(list(reversed(copy.deepcopy(complete["members"]))))
        first = decide({"phase": "match", "state": complete, "memory": None}, "adaptive_greedy")
        second = decide({"phase": "match", "state": permuted, "memory": None}, "adaptive_greedy")
        self.assertEqual(first, second)
        self.assertTrue(all(pair == sorted(pair) for pair in first["pairs"]))

    def test_ask_budget_boundaries_and_duplicate_member_rows(self):
        members = []
        for index in range(6):
            member = complete_member(f"m{index:03d}", arrived_day=index % 2)
            member["fields"]["age_min"] = None
            member["field_status"]["age_min"] = "not_asked"
            member["field_observed_day"]["age_min"] = None
            members.append(member)
        members.append(copy.deepcopy(members[0]))
        for budget, expected in ((0, 0), (1, 0), (2, 0), (3, 1), (11, 3), (12, 4)):
            current = state(copy.deepcopy(members), budget)
            current["day"] = 1
            asks = plan_asks(current, "adaptive_greedy")
            self.assertEqual(len(asks), expected)
            self.assertEqual(len({row["member_id"] for row in asks}), len(asks))

    def test_conflicting_duplicate_member_is_excluded_independent_of_order(self):
        original = complete_member("duplicate")
        conflict = copy.deepcopy(original)
        conflict["pool_id"] = "other"
        peer = complete_member("peer")
        for rows in ([original, conflict, peer], [conflict, peer, original]):
            current = state(copy.deepcopy(rows))
            response = decide({"phase": "match", "state": current, "memory": None}, "adaptive_greedy")
            self.assertEqual(response["pairs"], [])

            for row in current["members"][:2]:
                if row["member_id"] == "duplicate":
                    row["fields"]["age_min"] = None
                    row["field_status"]["age_min"] = "not_asked"
                    row["field_observed_day"]["age_min"] = None
            self.assertNotIn("duplicate", {ask["member_id"] for ask in plan_asks(current, "adaptive_greedy")})

    def test_inconsistent_field_status_or_future_observation_fails_closed(self):
        peer = complete_member("peer")
        cases = []
        observed_null = complete_member("bad")
        observed_null["fields"]["relationship_goal"] = None
        cases.append(observed_null)
        declined_value = complete_member("bad")
        declined_value["field_status"]["age_min"] = "declined"
        cases.append(declined_value)
        future_observation = complete_member("bad")
        future_observation["field_observed_day"]["age_min"] = 1
        cases.append(future_observation)
        for malformed in cases:
            current = state([malformed, copy.deepcopy(peer)])
            response = decide({"phase": "match", "state": current, "memory": None}, "adaptive_greedy")
            self.assertEqual(response["pairs"], [])
            self.assertEqual(plan_asks(current, "adaptive_greedy"), [])

    def test_non_mapping_memory_is_safely_reinitialized(self):
        empty = state([])
        for memory in ([], "stale", 7, True, {"bad": float("nan"), "blob": "x" * 100000}):
            response = decide({"phase": "match", "state": empty, "memory": memory}, "adaptive_greedy")
            json.dumps(response, allow_nan=False)
            self.assertIsInstance(response["memory"], dict)
            self.assertNotIn("bad", response["memory"])

    def test_unknown_future_fields_do_not_change_actions(self):
        base = state([complete_member("a"), complete_member("b")])
        extended = copy.deepcopy(base)
        extended["future_state_field"] = {"ignored": True}
        for member in extended["members"]:
            member["future_member_field"] = [1, 2, 3]
        request = lambda value: {"phase": "match", "state": value, "memory": None}
        self.assertEqual(decide(request(base), "adaptive_greedy"), decide(request(extended), "adaptive_greedy"))

    def test_replayed_request_is_idempotent_and_memory_is_small(self):
        current = state([complete_member(f"m{index:03d}") for index in range(40)])
        request = {"phase": "match", "state": current, "memory": {"old": "value"}}
        first = decide(copy.deepcopy(request), "adaptive_greedy")
        second = decide(copy.deepcopy(request), "adaptive_greedy")
        self.assertEqual(first, second)
        self.assertLess(len(json.dumps(first["memory"], allow_nan=False).encode()), 1024)

    def test_near_limit_ignored_payload_stays_valid(self):
        current = state([complete_member("a"), complete_member("b")])
        current["future_padding"] = "x" * 900_000
        request = {"schema_version": "1.0.0", "phase": "match", "state": current, "memory": None}
        self.assertLess(len(json.dumps(request).encode()), 1024 * 1024)
        response, _ = invoke([sys.executable, "policy.py"], request, timeout=10)
        self.assertEqual(response["pairs"], [["a", "b"]])

    def test_near_limit_constraint_arrays_stay_inside_runtime_limit(self):
        left = complete_member("a")
        right = complete_member("b")
        large = [f"zone_{index:05d}" for index in range(22_000)] + ["zone_a"]
        left["fields"]["acceptable_zones"] = large
        right["fields"]["acceptable_zones"] = list(reversed(large))
        request = {
            "schema_version": "1.0.0", "phase": "match",
            "state": state([left, right]), "memory": None,
        }
        self.assertLess(len(json.dumps(request).encode()), 1024 * 1024)
        started = time.perf_counter()
        response, _ = invoke([sys.executable, "policy.py"], request, timeout=10)
        self.assertEqual(response["pairs"], [["a", "b"]])
        self.assertLess(time.perf_counter() - started, 10)

    def test_mixed_pools_and_reversed_prior_pair_are_never_crossed(self):
        members = [complete_member("a"), complete_member("b"), complete_member("c")]
        members[2]["pool_id"] = "other"
        current = state(members)
        current["introductions"] = [{"user_a": "b", "user_b": "a"}]
        response = decide({"phase": "match", "state": current, "memory": None}, "adaptive_greedy")
        self.assertEqual(response["pairs"], [])

    def test_imbalanced_pools_and_single_feasible_edge(self):
        left = complete_member("large_a")
        right = complete_member("large_b")
        isolated = [complete_member(f"single_{index}") for index in range(12)]
        for index, member in enumerate(isolated):
            member["pool_id"] = f"singleton_{index}"
        current = state([left, right, *isolated])
        response = decide({"phase": "match", "state": current, "memory": None}, "adaptive_greedy")
        self.assertEqual(response["pairs"], [["large_a", "large_b"]])

    def test_odd_population_sizes_leave_exactly_one_member_unmatched(self):
        for size in (1, 3, 199, 201):
            current = state([complete_member(f"m{index:03d}") for index in range(size)])
            response = decide({"phase": "match", "state": current, "memory": None}, "adaptive_greedy")
            self.assertEqual(len(response["pairs"]), size // 2)
            flattened = [member_id for pair in response["pairs"] for member_id in pair]
            self.assertEqual(len(flattened), len(set(flattened)))

    def test_wait_tie_challenger_changes_only_equal_score_priority(self):
        current = state([
            complete_member("z_old", arrived_day=0),
            complete_member("a_new", arrived_day=10),
            complete_member("b_new", arrived_day=10),
        ])
        current["day"] = 10
        incumbent = decide({"phase": "match", "state": current, "memory": None}, "adaptive_greedy")
        challenger = decide(
            {"phase": "match", "state": current, "memory": None},
            "adaptive_wait_tie_greedy",
        )
        self.assertEqual(incumbent["pairs"], [["a_new", "b_new"]])
        self.assertIn("z_old", challenger["pairs"][0])
        self.assertEqual(len(incumbent["pairs"]), len(challenger["pairs"]))

    def test_refreshed_match_state_can_remove_an_ask_phase_member(self):
        incomplete = complete_member("a")
        incomplete["fields"]["age_min"] = None
        incomplete["field_status"]["age_min"] = "not_asked"
        incomplete["field_observed_day"]["age_min"] = None
        ask_state = state([incomplete, complete_member("b")])
        asks = decide({"phase": "ask", "state": ask_state, "memory": None}, "adaptive_greedy")
        self.assertEqual(asks["asks"], [{"member_id": "a", "field": "constraints"}])

        refreshed = state([complete_member("a"), complete_member("b")])
        refreshed["members"][0]["available"] = False
        match = decide({"phase": "match", "state": refreshed, "memory": asks["memory"]}, "adaptive_greedy")
        self.assertEqual(match["pairs"], [])

    def test_randomized_states_preserve_matching_invariants(self):
        generator = random.Random(20261010)
        for case in range(80):
            members = []
            for index in range(generator.randint(0, 35)):
                member = complete_member(f"case{case:03d}_{index:03d}")
                member["pool_id"] = f"pool{generator.randrange(3)}"
                member["available"] = generator.random() > 0.2
                if generator.random() < 0.25:
                    field = generator.choice(HARD)
                    member["fields"][field] = None
                    member["field_status"][field] = "not_asked"
                    member["field_observed_day"][field] = None
                if generator.random() < 0.25:
                    member["fields"]["relationship_goal"] = generator.choice([None, "long_term", "exploring"])
                members.append(member)

            current = state(members)
            available_ids = [member["member_id"] for member in members if member["available"]]
            generator.shuffle(available_ids)
            current["introductions"] = [
                {"user_a": available_ids[pos], "user_b": available_ids[pos + 1]}
                for pos in range(0, min(len(available_ids) - 1, 6), 2)
            ]
            response = decide({"phase": "match", "state": current, "memory": None}, "adaptive_greedy")
            by_id = {member["member_id"]: member for member in members}
            past = {tuple(sorted((row["user_a"], row["user_b"]))) for row in current["introductions"]}
            used = set()
            for pair in response["pairs"]:
                self.assertEqual(pair, sorted(pair))
                self.assertFalse(used.intersection(pair))
                self.assertNotIn(tuple(pair), past)
                self.assertTrue(all(by_id[member_id]["available"] for member_id in pair))
                self.assertEqual(eligibility(by_id[pair[0]], by_id[pair[1]])["status"], "feasible")
                used.update(pair)

    def test_dense_graph_real_process_stays_inside_wall_clock_limit(self):
        dense = state([complete_member(f"syn_{index:032x}") for index in range(200)])
        started = time.perf_counter()
        response, _ = invoke(
            [sys.executable, "policy.py"],
            {"schema_version": "1.0.0", "phase": "match", "state": dense, "memory": None},
            timeout=10,
        )
        self.assertEqual(len(response["pairs"]), 100)
        self.assertLess(time.perf_counter() - started, 10)

    def test_python_hash_seed_cannot_change_output(self):
        request = {
            "schema_version": "1.0.0",
            "phase": "match",
            "state": state([complete_member(f"m{index:03d}") for index in range(20)]),
            "memory": None,
        }
        outputs = []
        for hash_seed in ("1", "99991"):
            environment = dict(os.environ, PYTHONHASHSEED=hash_seed)
            process = subprocess.run(
                [sys.executable, "policy.py"],
                input=json.dumps(request, allow_nan=False),
                text=True,
                capture_output=True,
                timeout=10,
                check=True,
                env=environment,
            )
            outputs.append(json.loads(process.stdout))
        self.assertEqual(outputs[0], outputs[1])

    def test_deadline_and_msmi_boundaries_are_inclusive(self):
        intro = {
            "introduction_id": "i",
            "user_a": "a",
            "user_b": "b",
            "assigned_day": 10,
            "response_deadline_day": 17,
        }
        events = [
            {"event": "introduction_response", "member_id": "a", "value": "yes", "occurred_day": 17, "observed_day": 17},
            {"event": "introduction_response", "member_id": "b", "value": "yes", "occurred_day": 17, "observed_day": 17},
            {"event": "date_happened", "member_id": None, "value": True, "occurred_day": 40, "observed_day": 40},
            {"event": "second_meeting_intention", "member_id": "a", "value": "yes", "occurred_day": 43, "observed_day": 43},
            {"event": "second_meeting_intention", "member_id": "b", "value": "yes", "occurred_day": 43, "observed_day": 43},
        ]
        self.assertTrue(recorded_yes_by_deadline(intro, events, "a"))
        self.assertEqual(classify_funnel(intro, events), {
            "mutual_acceptance": True,
            "date_happened": True,
            "msmi": True,
        })
        swapped = dict(intro, user_a="b", user_b="a")
        self.assertEqual(classify_funnel(swapped, events), classify_funnel(intro, events))
        late = copy.deepcopy(events)
        late[-1]["occurred_day"] = late[-1]["observed_day"] = 44
        self.assertFalse(classify_funnel(intro, late)["msmi"])

    def test_impossible_event_order_and_duplicates_do_not_count(self):
        intro = {
            "introduction_id": "i",
            "user_a": "a",
            "user_b": "b",
            "assigned_day": 10,
            "response_deadline_day": 17,
        }
        before_assignment = [{
            "event": "introduction_response", "member_id": "a", "value": "yes",
            "occurred_day": 9, "observed_day": 9,
        }]
        with self.assertRaises(ValueError):
            recorded_yes_by_deadline(intro, before_assignment, "a")
        duplicate = before_assignment + [dict(before_assignment[0])]
        with self.assertRaises(ValueError):
            recorded_yes_by_deadline(intro, duplicate, "a")

    def test_invalid_event_actors_boolean_days_and_causal_order_are_rejected(self):
        intro = {
            "introduction_id": "i", "user_a": "a", "user_b": "b",
            "assigned_day": 10, "response_deadline_day": 17,
        }
        outsider = [{
            "event": "introduction_response", "member_id": "c", "value": "yes",
            "occurred_day": 11, "observed_day": 11,
        }]
        with self.assertRaises(ValueError):
            recorded_yes_by_deadline(intro, outsider, "a")

        boolean_day = [{
            "event": "introduction_response", "member_id": "a", "value": "yes",
            "occurred_day": True, "observed_day": True,
        }]
        with self.assertRaises(ValueError):
            recorded_yes_by_deadline(intro, boolean_day, "a")

        impossible = [
            {"event": "introduction_response", "member_id": "a", "value": "yes", "occurred_day": 13, "observed_day": 13},
            {"event": "introduction_response", "member_id": "b", "value": "yes", "occurred_day": 14, "observed_day": 14},
            {"event": "date_happened", "member_id": None, "value": True, "occurred_day": 12, "observed_day": 12},
        ]
        with self.assertRaises(ValueError):
            classify_funnel(intro, impossible)

        wrong_date_actor = [dict(impossible[-1], member_id="a")]
        with self.assertRaises(ValueError):
            classify_funnel(intro, wrong_date_actor)

    def test_event_stage_deadline_and_introduction_identity_are_strict(self):
        intro = {
            "introduction_id": "i", "user_a": "a", "user_b": "b",
            "assigned_day": 10, "response_deadline_day": 17,
        }
        with self.assertRaises(ValueError):
            validate_event_sequence(dict(intro, response_deadline_day=18), [])

        wrong_intro = [{
            "introduction_id": "other", "event": "introduction_response",
            "member_id": "a", "value": "yes", "occurred_day": 11,
            "observed_day": 11,
        }]
        with self.assertRaises(ValueError):
            validate_event_sequence(intro, wrong_intro)

        second_without_date = [
            {"event": "introduction_response", "member_id": "a", "value": "yes", "occurred_day": 11, "observed_day": 11},
            {"event": "introduction_response", "member_id": "b", "value": "yes", "occurred_day": 12, "observed_day": 12},
            {"event": "second_meeting_intention", "member_id": "a", "value": "yes", "occurred_day": 14, "observed_day": 14},
        ]
        with self.assertRaises(ValueError):
            validate_event_sequence(intro, second_without_date)


if __name__ == "__main__":
    unittest.main()
