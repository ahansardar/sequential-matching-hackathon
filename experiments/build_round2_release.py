"""Build a deterministic hash manifest for the Round 2 submission files."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FILES = (
    "policy.py",
    "adaptive.py",
    "Dockerfile",
    "requirements.txt",
    "ROUND2_SUBMISSION.md",
    "README.md",
    "docs/DECISIONS.md",
    "docs/EDGE_CASE_REGISTER.md",
    "docs/FINAL_SUBMISSION_ISSUE.md",
    "experiments/round2_release_gate.py",
    "experiments/build_round2_pdf.py",
    "test_round2_release_gate.py",
    "output/pdf/LuminaX_Round2_Final_Report.pdf",
    "results/round2_summary.json",
    "results/round2_adaptive_greedy_101_103_all.json",
    "results/round2_greedy_101_103_all.json",
    "results/round2_no_asks_101_103_all.json",
    "results/round2_random_assembled_101_103_all.json",
    "results/round2_random_attempt1_timeout.json",
    "results/round2_random_attempt2_timeout.json",
    "results/round2_input_order_ablation_101_103_all.json",
    "results/container_check.json",
    "LUMINAX_LICENSE.md",
    "THIRD_PARTY_NOTICES.md",
)


def _release_bytes(path: Path) -> bytes:
    raw = path.read_bytes()
    return raw if path.suffix.lower() == ".pdf" else raw.replace(b"\r\n", b"\n")


def _sha256(path: Path) -> str:
    return hashlib.sha256(_release_bytes(path)).hexdigest()


def build_manifest() -> dict:
    paths = [ROOT / name for name in FILES]
    missing = [name for name, path in zip(FILES, paths) if not path.is_file()]
    if missing:
        raise ValueError(f"release files are missing: {missing}")

    report = (ROOT / "ROUND2_SUBMISSION.md").read_text(encoding="utf-8")
    if any(marker in report for marker in ("PENDING", "TODO", "<!--")):
        raise ValueError("Round 2 report contains an unresolved placeholder")
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    if "@sha256:" not in dockerfile:
        raise ValueError("Docker base image is not digest-pinned")

    summary = json.loads((ROOT / "results/round2_summary.json").read_text(encoding="utf-8"))
    expected_methods = {
        "adaptive_greedy",
        "greedy",
        "no_asks",
        "random",
        "adaptive_input_order_greedy",
    }
    if summary.get("submitted_method") != "adaptive_greedy":
        raise ValueError("wrong submitted method in Round 2 summary")
    if set(summary.get("methods", {})) != expected_methods:
        raise ValueError("Round 2 summary method set is incomplete")
    if any(not method["summary"].get("eligible") for method in summary["methods"].values()):
        raise ValueError("Round 2 summary contains an ineligible method")

    container = json.loads((ROOT / "results/container_check.json").read_text(encoding="utf-8"))
    if not container.get("summary", {}).get("eligible"):
        raise ValueError("container check is not eligible")
    if any(row.get("maximum_policy_call_seconds", 10) >= 10 for row in container["episodes"]):
        raise ValueError("container check reached the policy call time limit")

    return {
        "schema_version": "round2-release-1",
        "team": "LuminaX",
        "release_ref": "round2-final-v2",
        "submitted_method": "adaptive_greedy",
        "public_evidence": {
            "seeds": [101, 102, 103],
            "variants": [
                "development",
                "sparse",
                "cold_start",
                "delayed",
                "shift",
                "drift",
            ],
            "episodes_per_method": 18,
            "method_count": 5,
        },
        "files": {
            name: {
                "sha256": _sha256(path),
                "bytes": len(_release_bytes(path)),
            }
            for name, path in zip(FILES, paths)
        },
        "verification": {
            "unit_tests": 125,
            "public_data_files": 71,
            "container_episode_valid": True,
            "container_maximum_policy_call_seconds": max(
                row["maximum_policy_call_seconds"] for row in container["episodes"]
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "round2_release_manifest.json",
    )
    args = parser.parse_args()
    try:
        payload = build_manifest()
    except (FileNotFoundError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        parser.error(str(error))
    args.output.write_bytes(
        (json.dumps(payload, indent=2, allow_nan=False) + "\n").encode("utf-8")
    )
    print(json.dumps({
        "output": str(args.output),
        "files": len(payload["files"]),
        "release_ref": payload["release_ref"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
