"""Tests for directional probability calibration."""
from __future__ import annotations

import unittest

from experiments.directional_calibration import (
    calibration_metrics,
    equal_variant_metrics,
    paired_brier_difference_intervals,
    run_audit,
    seed_cluster_intervals,
)


class DirectionalCalibrationTests(unittest.TestCase):
    def test_perfect_predictions_have_zero_brier_and_log_loss(self):
        rows = [
            {"label": 0, "prediction": 0.0},
            {"label": 1, "prediction": 1.0},
        ]
        metrics = calibration_metrics(rows)
        self.assertEqual(metrics["brier_score"], 0.0)
        self.assertLess(metrics["log_loss"], 1e-9)
        self.assertEqual(metrics["auc"], 1.0)

    def test_seed_bootstrap_requires_complete_variant_groups(self):
        rows = [
            {"seed": 1, "variant": "development", "label": 1, "prediction": 0.5},
            {"seed": 1, "variant": "sparse", "label": 0, "prediction": 0.5},
            {"seed": 2, "variant": "development", "label": 1, "prediction": 0.5},
        ]
        with self.assertRaises(ValueError):
            seed_cluster_intervals(rows, 10, 7)

    def test_fit_calibration_and_holdout_seeds_must_be_disjoint(self):
        with self.assertRaises(ValueError):
            run_audit([1], [1], [2], ["development"], 1, 10, 7)

    def test_seed_splits_must_be_nonempty_and_unique(self):
        with self.assertRaises(ValueError):
            run_audit([], [2], [3], ["development"], 1, 10, 7)
        with self.assertRaises(ValueError):
            run_audit([1, 1], [2], [3], ["development"], 1, 10, 7)

    def test_auc_is_undefined_when_only_one_class_is_present(self):
        metrics = calibration_metrics([
            {"label": 0, "prediction": 0.1},
            {"label": 0, "prediction": 0.2},
        ])
        self.assertIsNone(metrics["auc"])

    def test_equal_variant_metrics_do_not_weight_busy_scenarios_more(self):
        rows = [
            {"variant": "quiet", "label": 0, "prediction": 0.0},
            *[
                {"variant": "busy", "label": 1, "prediction": 0.0}
                for _ in range(9)
            ],
        ]
        pooled = calibration_metrics(rows)
        macro = equal_variant_metrics(rows, ["quiet", "busy"])
        self.assertEqual(pooled["brier_score"], 0.9)
        self.assertEqual(macro["brier_score"], 0.5)

    def test_clustered_intervals_include_equal_count_ece(self):
        rows = [
            {"seed": seed, "variant": variant, "label": seed % 2, "prediction": 0.5}
            for seed in (1, 2)
            for variant in ("development", "sparse")
        ]
        intervals = seed_cluster_intervals(rows, 20, 7)
        self.assertIn("equal_count_expected_calibration_error", intervals["intervals"])
        self.assertIn("equal scenario weighting", intervals["method"])
        self.assertIn("fixed holdout", intervals["ece_bins"])

    def test_paired_brier_interval_preserves_seed_worlds(self):
        challenger = [
            {"seed": seed, "variant": variant, "target": "a", "label": seed % 2, "prediction": 0.4}
            for seed in (1, 2)
            for variant in ("development", "sparse")
        ]
        reference = [dict(row, prediction=0.5) for row in challenger]
        result = paired_brier_difference_intervals(challenger, reference, 20, 7)
        self.assertEqual(result["seed_groups"], 2)
        self.assertEqual(result["variants_per_seed"], 2)


if __name__ == "__main__":
    unittest.main()
