"""Verify the fixed 33-item closure boundary and publication artifacts."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "docs" / "EDGE_CASE_CLOSURE.md"
REPORT = ROOT / "ROUND1_CORRECTED_ADDENDUM.md"
PDF = ROOT / "output" / "pdf" / "LuminaX_Round1_Corrected_Addendum.pdf"
SIDECAR = PDF.with_suffix(".source.sha256")
REPLY = ROOT / "RECONSIDERATION_REPLY.md"
RESULTS = {
    "corrected_history_seed_grouped.json",
    "corrected_allocation_outcomes.json",
    "corrected_clarification_order.json",
    "corrected_safe_cardinality_no_history.json",
    "corrected_member_order.json",
    "corrected_wait_tie.json",
    "corrected_profile_completeness.json",
    "corrected_profile_completeness_all_masked.json",
    "corrected_directional_calibration.json",
    "corrected_sensitivity.json",
    "edge_case_audit.json",
}


def _run(*args):
    return subprocess.run(
        args, cwd=ROOT, check=True, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    ).stdout.strip()


def _closure_rows():
    text = REGISTER.read_text(encoding="utf-8")
    rows = re.findall(
        r"^\|\s*(\d+)\s*\|([^|]+)\|\s*(fixed|measured|contract-excluded)\s*\|([^|]+)\|$",
        text,
        flags=re.MULTILINE,
    )
    numbers = [int(row[0]) for row in rows]
    if numbers != list(range(1, 34)):
        raise AssertionError(f"closure register must contain exactly rows 1-33, got {numbers}")
    return rows


def _check_report_hash():
    expected = hashlib.sha256(REPORT.read_bytes()).hexdigest()
    fields = dict(
        line.split("  ", 1)
        for line in SIDECAR.read_text(encoding="ascii").splitlines()
        if "  " in line
    )
    if fields.get("markdown_sha256") != expected:
        raise AssertionError("report source hash does not match the PDF sidecar")
    if fields.get("pdf_file") != PDF.name or not PDF.is_file() or PDF.stat().st_size < 10_000:
        raise AssertionError("PDF is missing or does not match its sidecar")
    return expected


def _evidence_revision():
    text = REPLY.read_text(encoding="utf-8")
    revisions = set(re.findall(r"/blob/([0-9a-f]{40})/", text))
    if len(revisions) != 1:
        raise AssertionError("reconsideration links must pin one full evidence revision")
    return revisions.pop()


def run(check_remote=False):
    rows = _closure_rows()
    missing = sorted(name for name in RESULTS if not (ROOT / "results" / name).is_file())
    if missing:
        raise AssertionError(f"missing closure evidence: {missing}")
    policy = (ROOT / "policy.py").read_text(encoding="utf-8")
    if "default='adaptive_greedy'" not in policy:
        raise AssertionError("submitted policy default changed")
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    copy_tokens = {
        token
        for line in dockerfile.splitlines()
        if line.strip().upper().startswith("COPY ")
        for token in line.split()[1:]
    }
    for required in ("kit.py", "adaptive.py", "policy.py"):
        if required not in copy_tokens:
            raise AssertionError(f"runtime image whitelist is missing {required}")
    report = REPORT.read_text(encoding="utf-8")
    for result in RESULTS:
        if result not in report:
            raise AssertionError(f"report does not cite {result}")
    source_hash = _check_report_hash()
    revision = _evidence_revision()
    remote_checked = False
    if check_remote:
        remote_heads = _run("git", "ls-remote", "origin")
        if revision not in remote_heads:
            raise AssertionError("pinned evidence revision is not available on the remote")
        remote_checked = True
    counts = {
        state: sum(row[2] == state for row in rows)
        for state in ("fixed", "measured", "contract-excluded")
    }
    return {
        "status": "passed",
        "items_closed": len(rows),
        "closure_states": counts,
        "submitted_policy_mode": "adaptive_greedy",
        "evidence_revision": revision,
        "remote_revision_checked": remote_checked,
        "report_markdown_sha256": source_hash,
        "evidence_files": sorted(RESULTS),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--remote", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "closure_audit.json")
    args = parser.parse_args()
    payload = run(args.remote)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
