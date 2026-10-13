import json
from pathlib import Path
import tempfile
import unittest

from evaluate import VARIANTS, summarise
from experiments.build_round2_summary import (
    EXPECTED_SEEDS,
    build_summary,
)


def result_payload(method):
    rows = []
    for variant in VARIANTS:
        for seed in EXPECTED_SEEDS:
            rows.append({
                "seed": seed,
                "variant": variant,
                "valid": True,
                "assignments": 1,
                "mutual_acceptances": 1,
                "dates": 1,
                "mutual_second_meeting_intention": int(method == "adaptive_greedy"),
                "missing_feedback": 0,
                "ask_cost": 1,
                "arrived_members": 200,
                "msmi_per_100_arrived_members": (
                    0.5 if method == "adaptive_greedy" else 0.0
                ),
                "served_members": 2,
                "unserved_members": 198,
                "coverage": 0.01,
                "mutual_acceptances_per_100": 0.5,
                "first_introduction_wait_days": [0, 1],
                "inference_seconds": 0.01,
                "policy_calls": 120,
                "maximum_policy_call_seconds": 0.001,
            })
    return {
        "release": "1.0.0",
        "mode": "trusted_local",
        "episodes": rows,
        "summary": summarise(rows),
    }


class Round2SummaryTests(unittest.TestCase):
    def write_matrix(self, root):
        paths = {}
        for method in (
            "adaptive_greedy",
            "greedy",
            "no_asks",
            "random",
            "adaptive_input_order_greedy",
        ):
            path = root / f"{method}.json"
            path.write_text(json.dumps(result_payload(method)), encoding="utf-8")
            paths[method] = path
        return paths

    def test_complete_matrix_builds_paired_summary(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory:
            payload = build_summary(self.write_matrix(Path(directory)))
        self.assertEqual(payload["submitted_method"], "adaptive_greedy")
        self.assertEqual(payload["evidence_scope"]["episodes_per_method"], 18)
        self.assertEqual(payload["methods"]["adaptive_greedy"]["operational"]["episodes"], 18)
        self.assertEqual(
            payload["paired_submitted_minus_comparator"]["greedy"]["mean_primary_delta"],
            0.5,
        )

    def test_missing_episode_is_rejected(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory:
            paths = self.write_matrix(Path(directory))
            payload = json.loads(paths["random"].read_text(encoding="utf-8"))
            payload["episodes"].pop()
            paths["random"].write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "matrix is incomplete"):
                build_summary(paths)


if __name__ == "__main__":
    unittest.main()
