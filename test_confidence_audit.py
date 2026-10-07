"""Tests for the paired confidence audit."""
from __future__ import annotations

import unittest

from experiments.confidence_audit import paired_analysis, promotion_gate


def row(seed, variant, score):
    return {
        "seed": seed,
        "variant": variant,
        "msmi_per_100_arrived_members": score,
    }


class ConfidenceAuditTests(unittest.TestCase):
    def test_paired_analysis_uses_matched_scenarios(self):
        incumbent = [row(1, "development", 0.0), row(1, "sparse", 0.5)]
        challenger = [row(1, "development", 0.5), row(1, "sparse", 0.5)]
        result = paired_analysis(incumbent, challenger, resamples=100, seed=7)
        self.assertEqual(result["paired_episodes"], 2)
        self.assertEqual(result["mean_primary_delta"], 0.25)
        self.assertEqual(result["scenario_mean_deltas"]["development"], 0.5)

    def test_promotion_requires_every_gate(self):
        incumbent = {"eligible": True, "primary_score": 0.25}
        challenger = {"eligible": True, "primary_score": 0.30}
        analysis = {
            "scenario_mean_deltas": {"development": 0.05},
            "bootstrap": {"lower": 0.01},
        }
        self.assertTrue(promotion_gate(incumbent, challenger, analysis)["promote"])
        analysis["scenario_mean_deltas"]["development"] = -0.01
        self.assertFalse(promotion_gate(incumbent, challenger, analysis)["promote"])


if __name__ == "__main__":
    unittest.main()
