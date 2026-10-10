"""Verify the fixed 33-item closure boundary and publication artifacts."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "docs" / "EDGE_CASE_CLOSURE.md"
REPORT = ROOT / "ROUND1_CORRECTED_ADDENDUM.md"
PDF = ROOT / "output" / "pdf" / "LuminaX_Round1_Corrected_Addendum.pdf"
SIDECAR = PDF.with_suffix(".source.sha256")
REPLY = ROOT / "RECONSIDERATION_REPLY.md"
MANIFEST = ROOT / "release_manifest.json"


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


def _manifest():
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    required = {
        "schema_version", "release_ref", "repository_url", "report_source",
        "report_pdf", "report_sidecar", "evidence_files",
    }
    if set(payload) != required or payload["schema_version"] != 1:
        raise AssertionError("release manifest schema is invalid")
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]+", payload["release_ref"]):
        raise AssertionError("release reference is invalid")
    return payload


def _check_report_hash(manifest):
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
    pdf_hash = hashlib.sha256(PDF.read_bytes()).hexdigest()
    if fields.get("pdf_sha256") != pdf_hash:
        raise AssertionError("PDF hash does not match its sidecar")
    if manifest["report_source"] != REPORT.name:
        raise AssertionError("release manifest report source is invalid")
    if manifest["report_pdf"] != PDF.relative_to(ROOT).as_posix():
        raise AssertionError("release manifest PDF path is invalid")
    if manifest["report_sidecar"] != SIDECAR.relative_to(ROOT).as_posix():
        raise AssertionError("release manifest sidecar path is invalid")
    return expected, pdf_hash


def _check_release_links(manifest):
    release_ref = manifest["release_ref"]
    repository_url = manifest["repository_url"].rstrip("/")
    combined = REPORT.read_text(encoding="utf-8") + "\n" + REPLY.read_text(encoding="utf-8")
    if "/invitations" in combined:
        raise AssertionError("private GitHub invitations URL must not appear in release documents")
    if re.search(r"github\.com/[^/]+/[^/]+/(?:blob|tree)/[0-9a-f]{40}(?:/|\))", combined):
        raise AssertionError("release documents contain a stale commit-pinned file link")
    refs = re.findall(
        re.escape(repository_url) + r"/(?:blob|tree)/([^/)\s]+)",
        combined,
    )
    if not refs or set(refs) != {release_ref}:
        raise AssertionError("release documents do not use one manifest release reference")


def _check_remote(manifest):
    release_ref = quote(manifest["release_ref"], safe="")
    url = f"{manifest['repository_url'].rstrip('/')}/tree/{release_ref}"
    request = Request(url, headers={"User-Agent": "LuminaX-release-audit/1.0"})
    try:
        with urlopen(request, timeout=10) as response:
            if response.status >= 400:
                raise AssertionError(f"release URL returned HTTP {response.status}")
    except HTTPError as exc:
        if exc.code == 404:
            raise AssertionError("release reference is not available on GitHub") from exc
        return False, f"unavailable_http_{exc.code}", url
    except (URLError, TimeoutError, OSError):
        return False, "unavailable_in_environment", url
    return True, "available", url


def run(check_remote=False):
    manifest = _manifest()
    rows = _closure_rows()
    evidence_files = manifest["evidence_files"]
    missing = sorted(name for name in evidence_files if not (ROOT / name).is_file())
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
    for result in evidence_files:
        if Path(result).name not in report:
            raise AssertionError(f"report does not cite {result}")
    source_hash, pdf_hash = _check_report_hash(manifest)
    _check_release_links(manifest)
    remote_checked = False
    remote_status = "not_requested"
    release_url = f"{manifest['repository_url'].rstrip('/')}/tree/{manifest['release_ref']}"
    if check_remote:
        remote_checked, remote_status, release_url = _check_remote(manifest)
    counts = {
        state: sum(row[2] == state for row in rows)
        for state in ("fixed", "measured", "contract-excluded")
    }
    return {
        "status": "passed",
        "items_closed": len(rows),
        "closure_states": counts,
        "submitted_policy_mode": "adaptive_greedy",
        "release_ref": manifest["release_ref"],
        "release_url": release_url,
        "remote_revision_checked": remote_checked,
        "remote_check_status": remote_status,
        "report_markdown_sha256": source_hash,
        "report_pdf_sha256": pdf_hash,
        "evidence_files": sorted(evidence_files),
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
