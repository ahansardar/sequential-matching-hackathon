"""Structural tests for the fixed 33-item closure register."""
from __future__ import annotations

import unittest

from experiments.closure_audit import _closure_rows


class ClosureRegisterTests(unittest.TestCase):
    def test_register_has_exactly_the_fixed_33_items(self):
        rows = _closure_rows()
        self.assertEqual(len(rows), 33)
        self.assertEqual([int(row[0]) for row in rows], list(range(1, 34)))

    def test_every_item_has_a_closed_state(self):
        rows = _closure_rows()
        self.assertTrue(all(row[2] in {"fixed", "measured", "contract-excluded"} for row in rows))


if __name__ == "__main__":
    unittest.main()
