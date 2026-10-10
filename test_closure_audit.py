"""Structural tests for the fixed 33-item closure register."""
from __future__ import annotations

import unittest
from unittest.mock import patch
from urllib.error import URLError

from experiments.closure_audit import _check_remote, _closure_rows, _manifest, run


class ClosureRegisterTests(unittest.TestCase):
    def test_register_has_exactly_the_fixed_33_items(self):
        rows = _closure_rows()
        self.assertEqual(len(rows), 33)
        self.assertEqual([int(row[0]) for row in rows], list(range(1, 34)))

    def test_every_item_has_a_closed_state(self):
        rows = _closure_rows()
        self.assertTrue(all(row[2] in {"fixed", "measured", "contract-excluded"} for row in rows))

    def test_local_release_audit_passes_without_git_or_network(self):
        result = run(check_remote=False)
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["remote_check_status"], "not_requested")

    @patch("experiments.closure_audit.urlopen", side_effect=URLError("offline"))
    def test_remote_network_restriction_is_reported_without_crashing(self, _urlopen):
        checked, status, url = _check_remote(_manifest())
        self.assertFalse(checked)
        self.assertEqual(status, "unavailable_in_environment")
        self.assertTrue(url.endswith("/tree/round1-reconsideration-v1"))


if __name__ == "__main__":
    unittest.main()
