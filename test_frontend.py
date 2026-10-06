"""Safety and completeness checks for the local evaluation studio export."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from frontend.build_dashboard_data import build


class DashboardExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.output = Path(cls.temp_dir.name) / "dashboard.json"
        build(cls.output)
        cls.payload = json.loads(cls.output.read_text(encoding="utf-8"))

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    def test_export_covers_every_public_profile(self):
        self.assertEqual(len(self.payload["pools"]), 10)
        self.assertEqual(
            sum(len(pool["members"]) for pool in self.payload["poolDetails"].values()),
            2_000,
        )

    def test_member_rows_only_use_observable_fields(self):
        forbidden = {"truth", "latent", "response_rate", "second_bias", "seed"}
        for pool in self.payload["poolDetails"].values():
            for member in pool["members"]:
                self.assertTrue(forbidden.isdisjoint(member))
                self.assertTrue(forbidden.isdisjoint(member["fields"]))

    def test_every_selected_pair_is_a_scored_feasible_edge(self):
        for pool in self.payload["poolDetails"].values():
            edge_pairs = {(edge["left"], edge["right"]) for edge in pool["edges"]}
            for pair in pool["selectedPairs"]:
                self.assertIn(tuple(pair), edge_pairs)


if __name__ == "__main__":
    unittest.main()
