"""Tests for the permanent generated-seed use ledger."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from experiments.seed_registry import validate_registry


class SeedRegistryTests(unittest.TestCase):
    def test_repository_registry_has_no_accidental_reuse(self):
        result = validate_registry()
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["overlaps"], 0)

    def test_unapproved_overlap_is_rejected(self):
        payload = {
            "schema_version": "1.0",
            "entries": [
                {"name": "one", "role": "screen", "ranges": [[1, 2]], "reuse_group": None},
                {"name": "two", "role": "holdout", "ranges": [[2, 3]], "reuse_group": None},
            ],
        }
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "registry.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(ValueError):
                validate_registry(path)


if __name__ == "__main__":
    unittest.main()
