"""Tests for directional probability calibration."""
from __future__ import annotations

import unittest

from experiments.directional_calibration import calibration_metrics, run_audit, seed_cluster_intervals


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


if __name__ == "__main__":
    unittest.main()
