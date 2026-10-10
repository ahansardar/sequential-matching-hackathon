"""Tests for the paired confidence audit."""
from __future__ import annotations

import unittest

from experiments.confidence_audit import _parse_seeds, paired_analysis, promotion_gate


def row(seed, variant, score):
    return {
        "seed": seed,
        "variant": variant,
        "msmi_per_100_arrived_members": score,
    }


class ConfidenceAuditTests(unittest.TestCase):
    def test_seed_parser_accepts_ranges_and_rejects_reverse_ranges(self):
        self.assertEqual(_parse_seeds("4-6"), [4, 5, 6])
        self.assertEqual(_parse_seeds("4,6"), [4, 6])
        with self.assertRaises(ValueError):
            _parse_seeds("6-4")

    def test_paired_analysis_uses_matched_scenarios(self):
        incumbent = [row(1, "development", 0.0), row(1, "sparse", 0.5)]
        challenger = [row(1, "development", 0.5), row(1, "sparse", 0.5)]
        result = paired_analysis(incumbent, challenger, resamples=100, seed=7)
        self.assertEqual(result["paired_episodes"], 2)
        self.assertEqual(result["seed_groups"], 1)
        self.assertEqual(result["variants_per_seed"], 2)
        self.assertEqual(result["mean_primary_delta"], 0.25)
        self.assertEqual(result["scenario_mean_deltas"]["development"], 0.5)

    def test_seed_groups_are_resampled_as_complete_variant_blocks(self):
        incumbent = [
            row(1, "development", 0.0), row(1, "sparse", 0.0),
            row(2, "development", 0.0), row(2, "sparse", 0.0),
        ]
        challenger = [
            row(1, "development", 1.0), row(1, "sparse", 1.0),
            row(2, "development", -1.0), row(2, "sparse", -1.0),
        ]
        result = paired_analysis(incumbent, challenger, resamples=200, seed=3)
        self.assertEqual(result["bootstrap"]["resampling_unit"],
                         "whole seed group with every scenario variant")
        self.assertAlmostEqual(result["mean_primary_delta"], 0.0)

    def test_incomplete_seed_group_is_rejected(self):
        incumbent = [row(1, "development", 0.0), row(1, "sparse", 0.0),
                     row(2, "development", 0.0)]
        challenger = [row(1, "development", 0.0), row(1, "sparse", 0.0),
                      row(2, "development", 0.0)]
        with self.assertRaises(ValueError):
            paired_analysis(incumbent, challenger, resamples=10, seed=1)

    def test_duplicate_episode_is_rejected(self):
        incumbent = [row(1, "development", 0.0), row(1, "development", 0.0)]
        challenger = [row(1, "development", 0.0), row(1, "development", 0.0)]
        with self.assertRaises(ValueError):
            paired_analysis(incumbent, challenger, resamples=10, seed=1)

    def test_empty_input_is_rejected(self):
        with self.assertRaises(ValueError):
            paired_analysis([], [], resamples=10, seed=1)

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
