"""Tests for rejected objective-separation research policies."""
from __future__ import annotations

import unittest

from experiments.precise_policy import (
    HISTORY_SIGNAL_LIMIT,
    _confidence_weighted_history_signal,
    _greedy_pairs_lexicographic,
    _precise_batch,
    _raw_compatibility_guarded_batch,
)


class PrecisePolicyTests(unittest.TestCase):
    def test_confidence_weighted_history_is_centered_bounded_and_matures(self):
        self.assertAlmostEqual(_confidence_weighted_history_signal({}), 0.0)
        short = _confidence_weighted_history_signal({
            "response_trials": 1,
            "responses": 1,
            "accept_trials": 1,
            "accepts": 1,
        })
        mature = _confidence_weighted_history_signal({
            "response_trials": 8,
            "responses": 8,
            "accept_trials": 8,
            "accepts": 8,
        })
        self.assertGreater(mature, short)
        self.assertLessEqual(abs(mature), HISTORY_SIGNAL_LIMIT)

    def test_history_never_overrides_compatibility(self):
        compatibility = {("a", "b"): 7.0, ("a", "c"): 6.0}
        history = {("a", "b"): -6.0, ("a", "c"): 6.0}
        self.assertEqual(
            _greedy_pairs_lexicographic(compatibility, history),
            [("a", "b")],
        )

    def test_history_breaks_compatibility_ties(self):
        compatibility = {("a", "b"): 6.0, ("a", "c"): 6.0}
        history = {("a", "b"): -1.0, ("a", "c"): 1.0}
        self.assertEqual(
            _greedy_pairs_lexicographic(compatibility, history),
            [("a", "c")],
        )

    def test_precise_batch_rejects_lost_raw_compatibility(self):
        compatibility = {
            ("a", "b"): 6.0,
            ("a", "c"): 3.0,
            ("b", "d"): 2.0,
        }
        history = {pair: 0.0 for pair in compatibility}
        self.assertEqual(_precise_batch(compatibility, history), [("a", "b")])

    def test_precise_batch_accepts_safe_cardinality_gain(self):
        compatibility = {
            ("a", "b"): 6.0,
            ("a", "c"): 4.0,
            ("b", "d"): 4.0,
        }
        history = {pair: 0.0 for pair in compatibility}
        self.assertEqual(
            _precise_batch(compatibility, history),
            [("a", "c"), ("b", "d")],
        )

    def test_raw_guard_rejects_history_compensation(self):
        compatibility = {
            ("a", "b"): 6.0,
            ("a", "c"): 3.0,
            ("b", "d"): 2.0,
        }
        scored = {
            ("a", "b"): 600.0,
            ("a", "c"): 350.0,
            ("b", "d"): 350.0,
        }
        self.assertEqual(
            _raw_compatibility_guarded_batch(compatibility, scored),
            [("a", "b")],
        )


if __name__ == "__main__":
    unittest.main()
