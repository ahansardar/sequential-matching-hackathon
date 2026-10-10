"""Validate the permanent generated-seed use ledger."""
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "experiments" / "seed_registry.json"


def _expand(ranges):
    seeds = set()
    for bounds in ranges:
        if not isinstance(bounds, list) or len(bounds) != 2:
            raise ValueError("seed range must be [start, end]")
        start, end = bounds
        if type(start) is not int or type(end) is not int or start > end:
            raise ValueError("invalid seed range")
        seeds.update(range(start, end + 1))
    return seeds


def validate_registry(path=REGISTRY):
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("schema_version") != "1.0":
        raise ValueError("unknown seed registry schema")
    names = [entry.get("name") for entry in payload.get("entries", [])]
    if not names or len(names) != len(set(names)):
        raise ValueError("seed registry names must be unique and nonempty")
    owners = {}
    for entry in payload["entries"]:
        if not entry.get("role"):
            raise ValueError(f"seed registry role missing for {entry['name']}")
        for seed in _expand(entry.get("ranges", [])):
            previous = owners.get(seed)
            if previous is not None:
                groups = {previous.get("reuse_group"), entry.get("reuse_group")}
                if None in groups or len(groups) != 1:
                    raise ValueError(
                        f"seed {seed} is reused by {previous['name']} and {entry['name']}"
                    )
            owners[seed] = entry

    expected = {
        "history_confirmation_and_corrected_reanalysis": set(range(4001, 4021)),
        "directional_model_fit_reserved": set(range(6001, 6021)),
        "directional_calibration_reserved": set(range(6031, 6041)),
        "directional_final_holdout_reserved": set(range(6101, 6121)),
        "profile_service_and_masking_reserved": set(range(6201, 6221)),
        "guarded_allocation_outcomes": set(range(6301, 6311)),
        "clarification_order": set(range(6401, 6411)),
        "safe_cardinality_without_history": set(range(6501, 6511)),
        "stable_member_order": set(range(7201, 7221)),
        "edge_case_permutations": set(range(7301, 7303)),
        "equal_score_wait_tie": set(range(7401, 7411)),
    }
    by_name = {entry["name"]: _expand(entry["ranges"]) for entry in payload["entries"]}
    for name, seeds in expected.items():
        if by_name.get(name) != seeds:
            raise ValueError(f"registered range changed for {name}")
    return {
        "status": "passed",
        "entries": len(payload["entries"]),
        "unique_seeds": len(owners),
        "overlaps": 0,
    }


if __name__ == "__main__":
    print(json.dumps(validate_registry(), indent=2))
