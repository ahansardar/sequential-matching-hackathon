"""Adversarial boundary tests for the submitted policy and evidence rules."""
from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import time
import unittest

from adaptive import decide, plan_asks
from evaluate import invoke
from experiments.outcome_events import classify_funnel, recorded_yes_by_deadline
from kit import HARD, SOFT


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
            members.append(member)
        members.append(copy.deepcopy(members[0]))
        for budget, expected in ((0, 0), (1, 0), (2, 0), (3, 1), (11, 3), (12, 4)):
            asks = plan_asks(state(copy.deepcopy(members), budget), "adaptive_greedy")
            self.assertEqual(len(asks), expected)
            self.assertEqual(len({row["member_id"] for row in asks}), len(asks))

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
        self.assertFalse(recorded_yes_by_deadline(intro, before_assignment, "a"))
        duplicate = before_assignment + [dict(before_assignment[0])]
        with self.assertRaises(ValueError):
            recorded_yes_by_deadline(intro, duplicate, "a")


if __name__ == "__main__":
    unittest.main()
