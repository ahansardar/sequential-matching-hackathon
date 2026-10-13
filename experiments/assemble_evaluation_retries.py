"""Assemble a complete evaluation matrix from official per-episode reruns."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluate import summarise  # noqa: E402


RUNTIME_FIELDS = {
    "inference_seconds",
    "maximum_policy_call_seconds",
    "p95_policy_call_seconds",
}
HEADER_FIELDS = (
    "release",
    "mode",
    "decision_days",
    "follow_up_days",
    "members_per_episode",
)


def _digest(path: Path) -> str:
    canonical = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(canonical).hexdigest()


def _key(row: dict) -> tuple[str, int]:
    return row["variant"], row["seed"]


def _outcome(row: dict) -> dict:
    return {key: value for key, value in row.items() if key not in RUNTIME_FIELDS}


def assemble(paths: list[Path]) -> dict:
    if len(paths) < 2:
        raise ValueError("provide at least two official evaluation files")
    payloads = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
    header = {field: payloads[0].get(field) for field in HEADER_FIELDS}
    for payload in payloads[1:]:
        if any(payload.get(field) != value for field, value in header.items()):
            raise ValueError("evaluation headers do not match")

    key_sets = [{_key(row) for row in payload.get("episodes", [])} for payload in payloads]
    if not key_sets[0] or any(keys != key_sets[0] for keys in key_sets[1:]):
        raise ValueError("evaluation files do not contain the same episode keys")

    selected = []
    selected_sources = {}
    for key in sorted(key_sets[0]):
        valid_rows = []
        for source_index, payload in enumerate(payloads):
            matches = [row for row in payload["episodes"] if _key(row) == key]
            if len(matches) != 1:
                raise ValueError(f"episode {key} is missing or duplicated")
            if matches[0].get("valid"):
                valid_rows.append((source_index, matches[0]))
        if not valid_rows:
            raise ValueError(f"episode {key} has no valid rerun")
        expected = _outcome(valid_rows[0][1])
        if any(_outcome(row) != expected for _, row in valid_rows[1:]):
            raise ValueError(f"valid reruns disagree for episode {key}")
        source_index, row = valid_rows[0]
        selected.append(row)
        selected_sources[f"{key[0]}:{key[1]}"] = source_index

    summary = summarise(selected)
    if not summary.get("eligible"):
        raise ValueError("assembled matrix is not eligible")
    return {
        **header,
        "episodes": selected,
        "summary": summary,
        "assembly": {
            "reason": "per-episode rerun after transient local process timeout",
            "selection_rule": "first valid row in source order",
            "sources": [
                {
                    "file": path.name,
                    "sha256": _digest(path),
                }
                for path in paths
            ],
            "selected_source_index": selected_sources,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        payload = assemble(args.input)
    except (FileNotFoundError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        parser.error(str(error))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(
        (json.dumps(payload, indent=2, allow_nan=False) + "\n").encode("utf-8")
    )
    print(json.dumps({
        "output": str(args.output),
        "episodes": len(payload["episodes"]),
        "eligible": payload["summary"]["eligible"],
        "primary_score": payload["summary"]["primary_score"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
