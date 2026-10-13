import json
from pathlib import Path
import tempfile
import unittest

from experiments.assemble_evaluation_retries import assemble


def row(seed, valid=True, msmi=1):
    value = {
        "seed": seed,
        "variant": "development",
        "valid": valid,
    }
    if not valid:
        value["error"] = "Policy exceeded 10-second invocation limit"
        return value
    value.update({
        "assignments": 1,
        "mutual_acceptances": 1,
        "dates": 1,
        "mutual_second_meeting_intention": msmi,
        "missing_feedback": 0,
        "ask_cost": 3,
        "arrived_members": 200,
        "msmi_per_100_arrived_members": msmi * 0.5,
        "served_members": 2,
        "unserved_members": 198,
        "coverage": 0.01,
        "mutual_acceptances_per_100": 0.5,
        "first_introduction_wait_days": [0, 1],
        "inference_seconds": 1.0,
        "policy_calls": 120,
        "maximum_policy_call_seconds": 0.1,
        "p95_policy_call_seconds": 0.05,
        "action_sha256": f"action-{seed}",
    })
    return value


def payload(rows):
    return {
        "release": "1.0.0",
        "mode": "trusted_local",
        "decision_days": 60,
        "follow_up_days": 40,
        "members_per_episode": 200,
        "episodes": rows,
        "summary": {"eligible": False},
    }


class EvaluationRetryTests(unittest.TestCase):
    def write(self, root, name, value):
        path = root / name
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def test_complementary_valid_reruns_form_an_eligible_matrix(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory:
            root = Path(directory)
            first = self.write(root, "first.json", payload([row(1), row(2, False)]))
            second = self.write(root, "second.json", payload([row(1), row(2)]))
            result = assemble([first, second])
        self.assertTrue(result["summary"]["eligible"])
        self.assertEqual(len(result["episodes"]), 2)
        self.assertEqual(result["assembly"]["selected_source_index"]["development:2"], 1)

    def test_disagreeing_valid_outcomes_are_rejected(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory:
            root = Path(directory)
            first = self.write(root, "first.json", payload([row(1, msmi=1)]))
            second = self.write(root, "second.json", payload([row(1, msmi=0)]))
            with self.assertRaisesRegex(ValueError, "reruns disagree"):
                assemble([first, second])


if __name__ == "__main__":
    unittest.main()
