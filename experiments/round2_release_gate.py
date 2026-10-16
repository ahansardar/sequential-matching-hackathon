"""Fail-closed checks for the complete Round 2 release package."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
EXPECTED_METHOD_FILES = {
    "adaptive_greedy": "results/round2_adaptive_greedy_101_103_all.json",
    "greedy": "results/round2_greedy_101_103_all.json",
    "no_asks": "results/round2_no_asks_101_103_all.json",
    "random": "results/round2_random_assembled_101_103_all.json",
    "adaptive_input_order_greedy": (
        "results/round2_input_order_ablation_101_103_all.json"
    ),
}
REQUIRED_MANIFEST_FILES = {
    "policy.py",
    "adaptive.py",
    "Dockerfile",
    "ROUND2_SUBMISSION.md",
    "output/pdf/LuminaX_Round2_Final_Report.pdf",
    "results/round2_summary.json",
    "experiments/round2_release_gate.py",
    *EXPECTED_METHOD_FILES.values(),
}
COMMIT_TOKEN = "FULL_COMMIT_SHA"
COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
REQUIRED_SUBMITTED_COMMAND = (
    "python evaluate.py --baseline adaptive_greedy --seeds 101,102,103 "
    "--variants all"
)


def _release_bytes(path: Path) -> bytes:
    raw = path.read_bytes()
    return raw if path.suffix.lower() == ".pdf" else raw.replace(b"\r\n", b"\n")


def _sha256(path: Path) -> str:
    return hashlib.sha256(_release_bytes(path)).hexdigest()


def _json(path: Path) -> dict:
    return json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=lambda value: (_ for _ in ()).throw(
            ValueError(f"non-finite JSON value {value} in {path}")
        ),
    )


def _resolve_commit(commit: str, root: Path) -> str:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "--verify", f"{commit}^{{commit}}"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip().lower()
        tag = subprocess.run(
            ["git", "rev-parse", "--verify", "round2-final-v2^{commit}"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip().lower()
    except (FileNotFoundError, subprocess.CalledProcessError) as error:
        raise ValueError(f"cannot resolve commit {commit!r}: {error}") from error
    resolved = completed.stdout.strip().lower()
    if not COMMIT_PATTERN.fullmatch(resolved):
        raise ValueError(f"git returned an invalid commit: {resolved!r}")
    if resolved != head:
        raise ValueError("assessed commit is not the current HEAD")
    if resolved != tag:
        raise ValueError("round2-final-v2 tag does not point to the assessed commit")
    return resolved


def _check_commit_snapshot(root: Path, commit: str) -> list[str]:
    errors: list[str] = []
    manifest = _json(root / "round2_release_manifest.json")
    paths = [*manifest.get("files", {}), "round2_release_manifest.json"]
    for name in paths:
        try:
            subprocess.run(
                ["git", "cat-file", "-e", f"{commit}:{name}"],
                cwd=root,
                check=True,
                capture_output=True,
            )
        except (FileNotFoundError, subprocess.CalledProcessError):
            errors.append(f"assessed commit does not contain release file: {name}")
    if not errors:
        changed = subprocess.run(
            ["git", "diff", "--quiet", commit, "--", *paths],
            cwd=root,
            check=False,
        )
        if changed.returncode != 0:
            errors.append("working release files differ from the assessed commit")
    return errors


def render_issue(template: str, commit: str) -> str:
    if template.count(COMMIT_TOKEN) < 2:
        raise ValueError("submission issue template is missing commit placeholders")
    rendered = template.replace(COMMIT_TOKEN, commit)
    if COMMIT_TOKEN in rendered:
        raise ValueError("submission issue still contains a commit placeholder")
    return rendered


def _check_issue_template(root: Path, commit: str | None) -> tuple[list[str], str | None]:
    errors: list[str] = []
    path = root / "docs" / "FINAL_SUBMISSION_ISSUE.md"
    text = path.read_text(encoding="utf-8")
    if "LuminaX, 2 participants." not in text:
        errors.append("issue text must identify only LuminaX and 2 participants")
    for private_name in ("Ahan Sardar", "Enakshee Mondal"):
        if private_name in text:
            errors.append(f"issue text includes participant name: {private_name}")
    if "/invitations" in text:
        errors.append("issue text contains the private /invitations URL")
    if REQUIRED_SUBMITTED_COMMAND not in text:
        errors.append("issue text does not explicitly run adaptive_greedy")
    rendered = None
    if commit is not None:
        try:
            rendered = render_issue(text, commit)
        except ValueError as error:
            errors.append(str(error))
        if rendered is not None:
            refs = re.findall(
                r"https://github\.com/[^/\s]+/[^/\s]+/(?:tree|blob)/([^/\s`)]+)",
                rendered,
            )
            if not refs or any(ref != commit for ref in refs):
                errors.append("rendered issue has a mutable or invalid GitHub source link")
            if any(marker in rendered for marker in ("TODO", "PENDING", COMMIT_TOKEN)):
                errors.append("rendered issue has an unresolved placeholder")
    return errors, rendered


def _check_summary(root: Path) -> list[str]:
    errors: list[str] = []
    path = root / "results" / "round2_summary.json"
    summary = _json(path)
    if summary.get("submitted_method") != "adaptive_greedy":
        errors.append("summary submitted_method is not adaptive_greedy")
    if set(summary.get("methods", {})) != set(EXPECTED_METHOD_FILES):
        errors.append("summary does not contain the exact five-method matrix")
        return errors
    expected_keys = {
        (variant, seed)
        for variant in ("development", "sparse", "cold_start", "delayed", "shift", "drift")
        for seed in (101, 102, 103)
    }
    for method, expected_file in EXPECTED_METHOD_FILES.items():
        row = summary["methods"][method]
        if row.get("result_file") != expected_file:
            errors.append(f"{method}: summary points to the wrong result file")
            continue
        result_path = root / expected_file
        if not result_path.is_file():
            errors.append(f"{method}: result file is missing")
            continue
        if row.get("sha256") != _sha256(result_path):
            errors.append(f"{method}: result hash does not match summary")
        result = _json(result_path)
        episodes = result.get("episodes")
        keys = (
            {(episode.get("variant"), episode.get("seed")) for episode in episodes}
            if isinstance(episodes, list)
            else set()
        )
        if keys != expected_keys or len(episodes or []) != 18:
            errors.append(f"{method}: result is not the exact 18-episode matrix")
        if not result.get("summary", {}).get("eligible"):
            errors.append(f"{method}: result summary is ineligible")
        if any(not episode.get("valid") for episode in episodes or []):
            errors.append(f"{method}: result contains an invalid episode")
        if row.get("execution_mode") != result.get("mode"):
            errors.append(f"{method}: execution mode disagrees with result")
        if row.get("summary") != result.get("summary"):
            errors.append(f"{method}: reported metrics disagree with result")
    if not errors and root == ROOT:
        from experiments.build_round2_summary import build_summary

        rebuilt = build_summary({
            method: root / name for method, name in EXPECTED_METHOD_FILES.items()
        })
        if summary != rebuilt:
            errors.append("summary does not equal a fresh deterministic rebuild")
    return errors


def _check_container(root: Path) -> list[str]:
    errors: list[str] = []
    result = _json(root / "results" / "container_check.json")
    episodes = result.get("episodes", [])
    if result.get("mode") != "container":
        errors.append("container check was not run in container mode")
    if not result.get("summary", {}).get("eligible") or len(episodes) != 1:
        errors.append("container check must contain one eligible episode")
        return errors
    episode = episodes[0]
    if not episode.get("valid"):
        errors.append("container episode is invalid")
    if episode.get("policy_calls") != 120:
        errors.append("container episode does not contain 120 policy calls")
    if episode.get("maximum_policy_call_seconds", 10.0) >= 10.0:
        errors.append("container episode reached the 10-second call limit")
    if not re.fullmatch(r"[0-9a-f]{64}", str(episode.get("action_sha256", ""))):
        errors.append("container episode is missing a valid action hash")
    return errors


def _check_manifest(root: Path) -> list[str]:
    errors: list[str] = []
    manifest = _json(root / "round2_release_manifest.json")
    if manifest.get("release_ref") != "round2-final-v2":
        errors.append("manifest is not pinned to round2-final-v2")
    if not REQUIRED_MANIFEST_FILES.issubset(manifest.get("files", {})):
        errors.append("manifest omits required release files")
    for name, metadata in manifest.get("files", {}).items():
        path = root / name
        if not path.is_file():
            errors.append(f"manifest file is missing: {name}")
            continue
        if metadata.get("sha256") != _sha256(path):
            errors.append(f"manifest hash mismatch: {name}")
        if metadata.get("bytes") != len(_release_bytes(path)):
            errors.append(f"manifest byte count mismatch: {name}")
    if root == ROOT:
        from experiments.build_round2_release import build_manifest

        if manifest != build_manifest():
            errors.append("manifest does not equal a fresh deterministic rebuild")
    return errors


def _check_pdf_parity(root: Path) -> list[str]:
    if root != ROOT:
        return []
    from experiments.build_round2_pdf import build_pdf

    with tempfile.TemporaryDirectory() as directory:
        rebuilt = Path(directory) / "round2.pdf"
        build_pdf(root / "ROUND2_SUBMISSION.md", rebuilt)
        if rebuilt.read_bytes() != (
            root / "output" / "pdf" / "LuminaX_Round2_Final_Report.pdf"
        ).read_bytes():
            return ["PDF does not equal a fresh deterministic report rebuild"]
    return []


def run_gate(root: Path = ROOT, commit: str | None = None) -> tuple[dict, str | None]:
    root = root.resolve()
    resolved_commit = _resolve_commit(commit, root) if commit else None
    errors: list[str] = []
    report = (root / "ROUND2_SUBMISSION.md").read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8")
    for name, text in (("report", report), ("README", readme)):
        if REQUIRED_SUBMITTED_COMMAND not in text:
            errors.append(f"{name} does not explicitly run adaptive_greedy")
        if "/invitations" in text:
            errors.append(f"{name} contains the private /invitations URL")
    dockerfile = (root / "Dockerfile").read_text(encoding="utf-8")
    if "@sha256:" not in dockerfile:
        errors.append("Docker base image is not digest-pinned")
    copied = [line.strip() for line in dockerfile.splitlines() if line.strip().startswith("COPY ")]
    if copied != ["COPY kit.py adaptive.py policy.py ./"]:
        errors.append("Docker runtime file allowlist changed")
    errors.extend(_check_summary(root))
    errors.extend(_check_container(root))
    issue_errors, rendered_issue = _check_issue_template(root, resolved_commit)
    errors.extend(issue_errors)
    errors.extend(_check_manifest(root))
    errors.extend(_check_pdf_parity(root))
    if resolved_commit is not None:
        errors.extend(_check_commit_snapshot(root, resolved_commit))
    payload = {
        "schema_version": "round2-release-gate-1",
        "release_ref": "round2-final-v2",
        "commit": resolved_commit,
        "passed": not errors,
        "checks": {
            "submitted_method_explicit": True,
            "five_method_matrix": True,
            "result_hashes": True,
            "container_boundary": True,
            "privacy_safe_issue": True,
            "manifest_parity": True,
            "markdown_pdf_parity": True,
            "final_issue_rendered": resolved_commit is not None,
            "immutable_commit_snapshot": resolved_commit is not None,
        } if not errors else {},
        "errors": errors,
    }
    return payload, rendered_issue


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--commit")
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--render-issue", type=Path)
    args = parser.parse_args()
    if not args.commit and not args.preflight:
        parser.error("final validation requires --commit; use --preflight before the release commit")
    if args.preflight and args.render_issue:
        parser.error("--render-issue requires final validation with --commit")
    try:
        payload, rendered = run_gate(args.root, args.commit)
    except (FileNotFoundError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        payload, rendered = {
            "schema_version": "round2-release-gate-1",
            "release_ref": "round2-final-v2",
            "commit": None,
            "passed": False,
            "checks": {},
            "errors": [str(error)],
        }, None
    encoded = json.dumps(payload, indent=2, allow_nan=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8", newline="\n")
    print(encoded, end="")
    if args.render_issue:
        if rendered is None:
            parser.error("--render-issue requires a valid --commit and passing template checks")
        args.render_issue.parent.mkdir(parents=True, exist_ok=True)
        args.render_issue.write_text(rendered, encoding="utf-8", newline="\n")
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
