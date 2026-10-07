"""Tests for guarded-allocation activation telemetry."""
from __future__ import annotations

import unittest

from experiments.allocation_telemetry import episode_telemetry, summarise


class AllocationTelemetryTests(unittest.TestCase):
    def test_episode_covers_every_decision_day(self):
        result = episode_telemetry(5301, "sparse")
        self.assertEqual(result["days"], 60)
        self.assertLessEqual(result.get("global_used_days", 0), result["nonempty_days"])

    def test_summary_rates_use_the_correct_denominators(self):
        rows = [
            {"counts": {"days": 60, "nonempty_days": 20, "global_used_days": 2}},
            {"counts": {"days": 60, "nonempty_days": 30, "global_used_days": 3}},
        ]
        result = summarise(rows)
        self.assertEqual(result["global_rate_all_days"], 5 / 120)
        self.assertEqual(result["global_rate_nonempty_days"], 5 / 50)


if __name__ == "__main__":
    unittest.main()
