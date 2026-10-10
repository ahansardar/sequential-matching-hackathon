"""Tests for isolated policy-component comparisons."""
from __future__ import annotations

import unittest

from experiments.component_audit import _percentile


class ComponentAuditTests(unittest.TestCase):
    def test_percentile_handles_empty_and_interpolates(self):
        self.assertIsNone(_percentile([], 0.9))
        self.assertEqual(_percentile([0, 10], 0.5), 5)


if __name__ == "__main__":
    unittest.main()
