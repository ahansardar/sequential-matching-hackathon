"""Tests for the profile-completeness and controlled-masking audit."""
from __future__ import annotations

import unittest

from experiments.profile_completeness_audit import (
    arrival_band,
    completeness_band,
    group_seed_cluster_intervals,
    mask_soft_information,
    opportunity_band,
)
from kit import Simulator, SOFT, generate


class ProfileCompletenessAuditTests(unittest.TestCase):
    def test_completeness_bands_cover_every_possible_soft_count(self):
        self.assertEqual(
            [completeness_band(value) for value in range(8)],
            ["0", "1-2", "1-2", "3-6", "3-6", "3-6", "3-6", "7"],
        )

    def test_service_strata_cover_arrival_and_opportunity_boundaries(self):
        self.assertEqual([opportunity_band(value) for value in (0, 1, 4, 5, 14, 15)], [
            "0", "1-4", "1-4", "5-14", "5-14", "15+",
        ])
        self.assertEqual([arrival_band(value) for value in (0, 1, 10, 11, 20)], [
            "0", "1-10", "1-10", "11-20", "11-20",
        ])

    def test_mask_is_deterministic_and_never_changes_hard_fields(self):
        state = Simulator(generate(6201, 40, "test", "development")).observe()
        first = mask_soft_information(state, 6201, 0.5)
        second = mask_soft_information(state, 6201, 0.5)
        self.assertEqual(first, second)
        for original, masked in zip(state["members"], first["members"]):
            for field in original["fields"]:
                if field not in SOFT:
                    self.assertEqual(original["fields"][field], masked["fields"][field])

    def test_full_mask_hides_observed_soft_fields_without_mutating_source(self):
        state = Simulator(generate(6202, 40, "test", "development")).observe()
        original_observed = sum(
            member["fields"].get(field) is not None
            for member in state["members"]
            for field in SOFT
        )
        masked = mask_soft_information(state, 6202, 1.0)
        self.assertGreater(original_observed, 0)
        self.assertTrue(all(
            member["fields"].get(field) is None
            for member in masked["members"]
            for field in SOFT
        ))
        self.assertEqual(
            original_observed,
            sum(
                member["fields"].get(field) is not None
                for member in state["members"]
                for field in SOFT
            ),
        )

    def test_group_intervals_resample_complete_seed_worlds(self):
        rows = []
        for seed in (1, 2):
            for variant in ("development", "sparse"):
                groups = {}
                for band in ("0", "1-2", "3-6", "7"):
                    groups[band] = {
                        "members": 10,
                        "served_members": seed,
                        "unserved_members": 10 - seed,
                        "msmi_members": seed - 1,
                        "available_member_days": 50,
                        "observable_opportunity_member_days": 25,
                        "assignments": seed,
                        "decision_window_wait_sum": 80 - seed,
                    }
                rows.append({"seed": seed, "variant": variant, "groups": groups})
        result = group_seed_cluster_intervals(rows, 50, 7)
        self.assertEqual(result["0"]["seed_groups"], 2)
        self.assertEqual(result["0"]["variants_per_seed"], 2)
        self.assertIn("coverage", result["0"]["intervals"])


if __name__ == "__main__":
    unittest.main()
