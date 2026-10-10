"""Tests for seed-level robustness statistics."""
from __future__ import annotations

import unittest

from experiments.sensitivity_audit import exact_sign_flip_p_value, sensitivity


class SensitivityAuditTests(unittest.TestCase):
    def test_balanced_differences_have_no_sign_flip_evidence(self):
        self.assertEqual(exact_sign_flip_p_value([1.0, -1.0]), 1.0)

    def test_leave_one_out_and_detectable_effect_are_reported(self):
        result = sensitivity([0.0, 1.0, 2.0])
        self.assertEqual(result["mean_difference"], 1.0)
        self.assertEqual(result["leave_one_seed_out_minimum"], 0.5)
        self.assertEqual(result["leave_one_seed_out_maximum"], 1.5)
        self.assertGreater(result["minimum_detectable_effect_80pct_approx"], 0)


if __name__ == "__main__":
    unittest.main()
