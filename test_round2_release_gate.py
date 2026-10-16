from pathlib import Path
import tempfile
import unittest

from experiments.round2_release_gate import (
    COMMIT_TOKEN,
    _check_issue_template,
    _check_manifest,
    render_issue,
)


class Round2ReleaseGateTests(unittest.TestCase):
    def test_issue_renderer_replaces_every_commit_token(self):
        commit = "a" * 40
        rendered = render_issue(f"tree/{COMMIT_TOKEN}\nblob/{COMMIT_TOKEN}/report", commit)
        self.assertNotIn(COMMIT_TOKEN, rendered)
        self.assertEqual(rendered.count(commit), 2)

    def test_issue_renderer_rejects_incomplete_template(self):
        with self.assertRaisesRegex(ValueError, "missing commit placeholders"):
            render_issue(f"tree/{COMMIT_TOKEN}", "a" * 40)

    def test_issue_check_rejects_names_private_url_and_wrong_command(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory:
            root = Path(directory)
            docs = root / "docs"
            docs.mkdir()
            (docs / "FINAL_SUBMISSION_ISSUE.md").write_text(
                "LuminaX, 2 members: Ahan Sardar and Enakshee Mondal.\n"
                "https://github.com/example/repo/invitations\n"
                f"tree/{COMMIT_TOKEN}\nblob/{COMMIT_TOKEN}/report\n"
                "python evaluate.py --seeds 101,102,103 --variants all\n",
                encoding="utf-8",
            )
            errors, _ = _check_issue_template(root, "b" * 40)
        self.assertTrue(any("participant name" in error for error in errors))
        self.assertTrue(any("/invitations" in error for error in errors))
        self.assertTrue(any("adaptive_greedy" in error for error in errors))

    def test_issue_check_accepts_privacy_safe_immutable_text(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory:
            root = Path(directory)
            docs = root / "docs"
            docs.mkdir()
            (docs / "FINAL_SUBMISSION_ISSUE.md").write_text(
                "LuminaX, 2 participants.\n"
                "https://github.com/example/repo/tree/FULL_COMMIT_SHA\n"
                "https://github.com/example/repo/blob/FULL_COMMIT_SHA/report\n"
                "python evaluate.py --baseline adaptive_greedy --seeds 101,102,103 "
                "--variants all\n",
                encoding="utf-8",
            )
            errors, rendered = _check_issue_template(root, "c" * 40)
        self.assertEqual(errors, [])
        self.assertNotIn(COMMIT_TOKEN, rendered)

    def test_empty_manifest_is_rejected(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory:
            root = Path(directory)
            (root / "round2_release_manifest.json").write_text(
                '{"release_ref":"round2-final-v2","files":{}}',
                encoding="utf-8",
            )
            errors = _check_manifest(root)
        self.assertTrue(any("omits required" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
