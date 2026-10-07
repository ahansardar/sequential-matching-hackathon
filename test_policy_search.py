"""Safety checks for observable-only policy search helpers."""
from __future__ import annotations

from unittest import TestCase
from unittest.mock import patch

from experiments.search_observable_policy import _edges, _research_asks, _select_pairs
from kit import Simulator, baseline_asks, generate


class PolicySearchTests(TestCase):
    def test_incumbent_guard_rejects_lower_compatibility(self):
        incumbent = [("a", "b")]
        candidate = [("a", "c")]
        compatibility = {("a", "b"): 5.0, ("a", "c"): 4.0}
        edges = {("a", "b"): 500.0, ("a", "c"): 600.0}
        with (
            patch(
                "experiments.search_observable_policy.select_pairs",
                return_value=(incumbent, {}),
            ),
            patch(
                "experiments.search_observable_policy._refine_quality",
                return_value=candidate,
            ),
            patch(
                "experiments.search_observable_policy._compatibility_edges",
                return_value=compatibility,
            ),
        ):
            selected = _select_pairs({}, edges, {"protect_incumbent": True})
        self.assertEqual(selected, incumbent)

    def test_incumbent_guard_accepts_better_equal_compatibility_batch(self):
        incumbent = [("a", "b")]
        candidate = [("a", "c")]
        compatibility = {("a", "b"): 5.0, ("a", "c"): 5.0}
        edges = {("a", "b"): 500.0, ("a", "c"): 501.0}
        with (
            patch(
                "experiments.search_observable_policy.select_pairs",
                return_value=(incumbent, {}),
            ),
            patch(
                "experiments.search_observable_policy._refine_quality",
                return_value=candidate,
            ),
            patch(
                "experiments.search_observable_policy._compatibility_edges",
                return_value=compatibility,
            ),
        ):
            selected = _select_pairs({}, edges, {"protect_incumbent": True})
        self.assertEqual(selected, candidate)

    def test_expected_unlock_asks_are_valid_and_within_budget(self):
        state = Simulator(generate(4401, 80, "search_test", "cold_start")).observe()
        asks = _research_asks(
            state,
            {"ask_mode": "expected_unlock", "ask_soft_weight": 0.0},
        )
        self.assertLessEqual(3 * len(asks), state["ask_budget_remaining"])
        self.assertEqual(len(asks), len({ask["member_id"] for ask in asks}))
        self.assertTrue(all(ask["field"] == "constraints" for ask in asks))

    def test_missing_soft_credit_changes_only_research_edge_value(self):
        simulator = Simulator(generate(4402, 80, "search_test", "cold_start"))
        simulator.resolve_asks(baseline_asks(simulator.observe()))
        state = simulator.observe()
        base = {
            "soft_weights": [100] * 7,
            "signed_soft": False,
            "response_weight": 0.0,
            "accept_weight": 0.0,
            "second_weight": 0.0,
            "exploration_weight": 0.0,
            "prior_scale": 1.0,
            "threshold": -1e9,
        }
        without_credit = _edges(state, base)
        with_credit = _edges(state, dict(base, missing_soft_credit=0.25))
        self.assertEqual(without_credit.keys(), with_credit.keys())
        self.assertTrue(all(with_credit[pair] >= without_credit[pair] for pair in without_credit))


if __name__ == "__main__":
    import unittest

    unittest.main()
