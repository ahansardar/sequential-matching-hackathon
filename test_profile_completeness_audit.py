"""Tests for the profile-completeness and controlled-masking audit."""
from __future__ import annotations

import unittest

from experiments.profile_completeness_audit import (
    completeness_band,
    mask_soft_information,
)
from kit import Simulator, SOFT, generate


class ProfileCompletenessAuditTests(unittest.TestCase):
    def test_completeness_bands_cover_every_possible_soft_count(self):
        self.assertEqual(
            [completeness_band(value) for value in range(8)],
            ["0", "1-2", "1-2", "3-6", "3-6", "3-6", "3-6", "7"],
        )

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


if __name__ == "__main__":
    unittest.main()
