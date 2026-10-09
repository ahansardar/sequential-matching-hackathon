"""Tests for the rejected but reproducible learned-scoring experiment."""
from __future__ import annotations

import json
import unittest

from kit import Simulator, baseline_asks, baseline_match, generate
from outcome_model import feedback_history, load_model, pair_comparisons, score_pair


class OutcomeModelTests(unittest.TestCase):
    def test_pair_comparisons_preserve_unknowns(self):
        members = Simulator(generate(3010, 20, "test", "cold_start")).observe()["members"]
        comparisons = pair_comparisons(members[0], members[1])
        self.assertTrue(all(value in (True, False, None) for value in comparisons.values()))

    def test_feedback_history_uses_only_observed_events(self):
        simulator = Simulator(generate(3011, 80, "test", "development"))
        for _ in range(3):
            simulator.resolve_asks(baseline_asks(simulator.observe()))
            simulator.advance(baseline_match(simulator.observe()))
        state = simulator.observe()
        expected_events = [
            event for event in state["feedback"]
            if event["event"] == "introduction_response"
        ]
        histories = feedback_history(state)
        self.assertEqual(
            sum(history["response_trials"] for history in histories.values()),
            len(expected_events),
        )

    def test_model_asset_is_finite_and_uses_declared_training_seeds(self):
        model = load_model()
        json.dumps(model, allow_nan=False)
        self.assertEqual(model["training"]["seeds"], list(range(2001, 2041)))
        self.assertEqual(model["training"]["episodes"], 240)

    def test_all_model_scores_are_probabilities(self):
        simulator = Simulator(generate(3012, 80, "test", "development"))
        simulator.resolve_asks(baseline_asks(simulator.observe()))
        state = simulator.observe()
        members = state["members"][:2]
        for mode in ("learned_static", "learned_history", "learned_funnel"):
            score = score_pair(state, members[0], members[1], mode=mode)
            self.assertGreaterEqual(score, 0)
            self.assertLessEqual(score, 1)


if __name__ == "__main__":
    unittest.main()
