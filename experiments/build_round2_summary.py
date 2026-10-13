"""Validate the Round 2 result matrix and build one reviewer-facing summary."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import statistics
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluate import VARIANTS  # noqa: E402
from experiments.confidence_audit import paired_analysis  # noqa: E402


DEFAULT_RESULTS = {
    "adaptive_greedy": ROOT / "results" / "round2_adaptive_greedy_101_103_all.json",
    "greedy": ROOT / "results" / "round2_greedy_101_103_all.json",
    "no_asks": ROOT / "results" / "round2_no_asks_101_103_all.json",
    "random": ROOT / "results" / "round2_random_assembled_101_103_all.json",
    "adaptive_input_order_greedy": (
        ROOT / "results" / "round2_input_order_ablation_101_103_all.json"
    ),
}
EXPECTED_SEEDS = (101, 102, 103)


def _read_result(path: Path) -> dict:
    raw = path.read_bytes()
    payload = json.loads(raw)
    payload["_file"] = path.relative_to(ROOT).as_posix()
    payload["_sha256"] = hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()
    return payload


def _episode_key(row: dict) -> tuple[str, int]:
    return row["variant"], row["seed"]


def _validate_method(method: str, payload: dict) -> None:
    rows = payload.get("episodes")
    summary = payload.get("summary")
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"{method}: episodes must be a non-empty list")
    if not isinstance(summary, dict) or not summary.get("eligible"):
        raise ValueError(f"{method}: every episode must be eligible")
    keys = [_episode_key(row) for row in rows]
    if len(keys) != len(set(keys)):
        raise ValueError(f"{method}: duplicate seed and variant episode")
    expected = {
        (variant, seed) for variant in VARIANTS for seed in EXPECTED_SEEDS
    }
    if set(keys) != expected:
        raise ValueError(f"{method}: result matrix is incomplete or uses wrong seeds")
    if any(not row.get("valid") for row in rows):
        raise ValueError(f"{method}: invalid episode found")


def _percentile(values: list[float], probability: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = probability * (len(ordered) - 1)
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def _operational_summary(rows: list[dict]) -> dict:
    waits = [wait for row in rows for wait in row["first_introduction_wait_days"]]
    calls = sum(row.get("policy_calls", 0) for row in rows)
    return {
        "episodes": len(rows),
        "assignments": sum(row["assignments"] for row in rows),
        "mutual_acceptances": sum(row["mutual_acceptances"] for row in rows),
        "dates": sum(row["dates"] for row in rows),
        "mutual_second_meeting_intention": sum(
            row["mutual_second_meeting_intention"] for row in rows
        ),
        "missing_feedback": sum(row["missing_feedback"] for row in rows),
        "served_members": sum(row["served_members"] for row in rows),
        "unserved_members": sum(row["unserved_members"] for row in rows),
        "first_introduction_wait_days": {
            "served_member_count": len(waits),
            "median": statistics.median(waits) if waits else None,
            "p90": _percentile(waits, 0.9),
            "maximum": max(waits) if waits else None,
        },
        "runtime": {
            "policy_calls": calls,
            "total_inference_seconds": sum(
                row["inference_seconds"] for row in rows
            ),
            "maximum_policy_call_seconds": max(
                (row.get("maximum_policy_call_seconds", 0.0) for row in rows),
                default=0.0,
            ),
        },
    }


def build_summary(result_paths: dict[str, Path]) -> dict:
    methods = {method: _read_result(path) for method, path in result_paths.items()}
    for method, payload in methods.items():
        _validate_method(method, payload)
    reference_keys = {
        _episode_key(row) for row in methods["adaptive_greedy"]["episodes"]
    }
    if any(
        {_episode_key(row) for row in payload["episodes"]} != reference_keys
        for payload in methods.values()
    ):
        raise ValueError("Methods do not use identical seed and variant episodes")

    submitted = methods["adaptive_greedy"]
    comparisons = {}
    for method in result_paths:
        if method == "adaptive_greedy":
            continue
        comparisons[method] = paired_analysis(
            methods[method]["episodes"],
            submitted["episodes"],
            resamples=20000,
            seed=1701,
        )

    return {
        "schema_version": "round2-summary-1",
        "team": "LuminaX",
        "submitted_method": "adaptive_greedy",
        "evidence_scope": {
            "source": "public synthetic simulator",
            "seeds": list(EXPECTED_SEEDS),
            "variants": list(VARIANTS),
            "episodes_per_method": len(reference_keys),
            "scenario_weighting": "equal mean across six scenario families",
            "inference_random_seed": None,
        },
        "methods": {
            method: {
                "result_file": payload["_file"],
                "sha256": payload["_sha256"],
                "execution_mode": payload["mode"],
                "summary": payload["summary"],
                "operational": _operational_summary(payload["episodes"]),
            }
            for method, payload in methods.items()
        },
        "paired_submitted_minus_comparator": comparisons,
        "interpretation": (
            "Public results validate the interface and compare methods on declared "
            "seeds. They do not estimate or guarantee the private score."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "results" / "round2_summary.json",
    )
    args = parser.parse_args()
    try:
        payload = build_summary(DEFAULT_RESULTS)
    except (FileNotFoundError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        parser.error(str(error))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(
        (json.dumps(payload, indent=2, allow_nan=False) + "\n").encode("utf-8")
    )
    print(json.dumps({
        "output": str(args.output),
        "submitted_method": payload["submitted_method"],
        "methods": list(payload["methods"]),
        "episodes_per_method": payload["evidence_scope"]["episodes_per_method"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
