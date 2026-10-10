"""Independently validate the evidence cited by the corrected addendum.

This script deliberately does not call the analysis helpers that produced the
JSON files. It checks study separation, complete seed-by-variant blocks and the
reported paired means directly from saved episode rows.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
import statistics
import sys


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
EXPECTED_VARIANTS = {
    "development", "sparse", "cold_start", "delayed", "shift", "drift",
}
PRIMARY = "msmi_per_100_arrived_members"


def _load(name):
    path = RESULTS / name
    payload = json.loads(path.read_text(encoding="utf-8"))
    _finite(payload, str(path))
    return payload


def _finite(value, location):
    if isinstance(value, dict):
        for key, item in value.items():
            _finite(item, f"{location}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _finite(item, f"{location}[{index}]")
    elif isinstance(value, float) and not math.isfinite(value):
        raise AssertionError(f"non-finite number at {location}")


def _keyed(rows, seeds, variants):
    expected = {(seed, variant) for seed in seeds for variant in variants}
    keyed = {(row["seed"], row["variant"]): row for row in rows}
    if len(keyed) != len(rows):
        raise AssertionError("duplicate seed/variant episode")
    if set(keyed) != expected:
        missing = sorted(expected - set(keyed))
        extra = sorted(set(keyed) - expected)
        raise AssertionError(f"incomplete study block: missing={missing}, extra={extra}")
    return keyed


def _assert_close(actual, expected, label, tolerance=1e-12):
    if not math.isclose(actual, expected, rel_tol=0.0, abs_tol=tolerance):
        raise AssertionError(f"{label}: reported {actual}, recomputed {expected}")


def _validate_analysis(analysis, before_rows, after_rows, seeds, variants, metric):
    before = _keyed(before_rows, seeds, variants)
    after = _keyed(after_rows, seeds, variants)
    deltas = [after[key][metric] - before[key][metric] for key in sorted(before)]
    _assert_close(analysis["mean_primary_delta"], statistics.mean(deltas), metric)
    if analysis["paired_episodes"] != len(deltas):
        raise AssertionError(f"wrong paired episode count for {metric}")
    if analysis["seed_groups"] != len(seeds):
        raise AssertionError(f"wrong seed group count for {metric}")
    if analysis["variants_per_seed"] != len(variants):
        raise AssertionError(f"wrong variants-per-seed count for {metric}")
    if analysis["bootstrap"]["resampling_unit"] != "whole seed group with every scenario variant":
        raise AssertionError("bootstrap does not declare whole-seed resampling")
    for variant in variants:
        variant_deltas = [
            after[(seed, variant)][metric] - before[(seed, variant)][metric]
            for seed in seeds
        ]
        _assert_close(
            analysis["scenario_mean_deltas"][variant],
            statistics.mean(variant_deltas),
            f"{metric}/{variant}",
        )


def _validate_component(filename):
    payload = _load(filename)
    design = payload["comparison_design"]
    seeds = design["seeds"]
    variants = design["variants"]
    if set(variants) != EXPECTED_VARIANTS:
        raise AssertionError(f"{filename} does not contain all six variants")
    before = payload["methods"][design["incumbent"]]["episodes"]
    after = payload["methods"][design["challenger"]]["episodes"]
    for metric, analysis in payload["paired_metrics"].items():
        _validate_analysis(analysis, before, after, seeds, variants, metric)
    return set(seeds)


def _validate_history():
    payload = _load("corrected_history_seed_grouped.json")
    seeds = sorted({
        row["seed"]
        for method in payload["methods"].values()
        for row in method["episodes"]
    })
    variants = sorted(EXPECTED_VARIANTS)
    before = payload["methods"][payload["incumbent"]]["episodes"]
    after = payload["methods"][payload["challenger"]]["episodes"]
    _validate_analysis(payload["paired_analysis"], before, after, seeds, variants, PRIMARY)
    interval = payload["paired_analysis"]["bootstrap"]
    if not interval["lower"] <= 0 <= interval["upper"]:
        raise AssertionError("history interval no longer includes zero")
    if payload["promotion_gate"]["promote"]:
        raise AssertionError("uncertain history component was promoted")
    return set(seeds)


def _validate_profile(filename, expected_rate):
    payload = _load(filename)
    design = payload["design"]
    seeds = design["seeds"]
    variants = design["variants"]
    before = payload["conditions"]["unmasked"]["episodes"]
    after = payload["conditions"]["masked"]["episodes"]
    before_keys = _keyed(before, seeds, variants)
    after_keys = _keyed(after, seeds, variants)
    if any(row["mask_rate"] != 0 for row in before_keys.values()):
        raise AssertionError("unmasked profile arm contains masked rows")
    if any(row["mask_rate"] != expected_rate for row in after_keys.values()):
        raise AssertionError("profile mask rate does not match the file")
    for metric, analysis in payload["paired_masked_minus_unmasked"].items():
        _validate_analysis(analysis, before, after, seeds, variants, metric)
    for condition in ("unmasked", "masked"):
        total = sum(group["members"] for group in payload["conditions"][condition]["groups"].values())
        episode_total = sum(row["arrived_members"] for row in payload["conditions"][condition]["episodes"])
        if total != episode_total:
            raise AssertionError(f"profile member total mismatch in {condition}")
    return set(seeds)


def _validate_calibration():
    payload = _load("corrected_directional_calibration.json")
    design = payload["design"]
    train = set(design["training_seeds"])
    calibrate = set(design["calibration_seeds"])
    holdout = set(design["holdout_seeds"])
    if train & calibrate or train & holdout or calibrate & holdout:
        raise AssertionError("directional calibration seed splits overlap")
    if set(design["variants"]) != EXPECTED_VARIANTS:
        raise AssertionError("directional calibration does not contain all variants")
    if payload["sample"]["right_censored_holdout_examples"] != 0:
        raise AssertionError("directional holdout contains right-censored examples")
    overall = payload["holdout"]["overall"]
    targets = payload["holdout"]["by_target"]
    if sum(item["examples"] for item in targets.values()) != overall["examples"]:
        raise AssertionError("directional target counts do not sum to the holdout")
    predictions = payload["holdout"]["predictions"]
    if len(predictions) != overall["examples"]:
        raise AssertionError("directional predictions do not match the holdout count")
    if any(not 0 <= row["prediction"] <= 1 for row in predictions):
        raise AssertionError("directional probability is outside zero through one")
    _assert_close(
        overall["observed_rate"],
        statistics.mean(row["label"] for row in predictions),
        "directional holdout observed rate",
    )
    _assert_close(
        overall["mean_prediction"],
        statistics.mean(row["prediction"] for row in predictions),
        "directional holdout mean prediction",
    )
    _assert_close(
        overall["brier_score"],
        statistics.mean(
            (row["prediction"] - row["label"]) ** 2 for row in predictions
        ),
        "directional holdout Brier score",
    )
    return train | calibrate | holdout


def main():
    study_seeds = {
        "history": _validate_history(),
        "allocation_with_history": _validate_component("corrected_allocation_outcomes.json"),
        "clarification": _validate_component("corrected_clarification_order.json"),
        "allocation_without_history": _validate_component("corrected_safe_cardinality_no_history.json"),
        "profile_half_mask": _validate_profile("corrected_profile_completeness.json", 0.5),
        "profile_all_mask": _validate_profile("corrected_profile_completeness_all_masked.json", 1.0),
        "directional_calibration": _validate_calibration(),
    }
    # The profile studies intentionally reuse the same worlds, including their
    # unmasked arm. Every other corrected study has its own seed block.
    names = list(study_seeds)
    for index, left_name in enumerate(names):
        for right_name in names[index + 1:]:
            allowed = {left_name, right_name} == {"profile_half_mask", "profile_all_mask"}
            overlap = study_seeds[left_name] & study_seeds[right_name]
            if overlap and not allowed:
                raise AssertionError(
                    f"study seed overlap between {left_name} and {right_name}: {sorted(overlap)}"
                )
    print(json.dumps({
        "status": "passed",
        "files": 7,
        "checks": [
            "finite JSON numbers",
            "complete seed-by-variant blocks",
            "no duplicate episodes",
            "paired deltas recomputed from raw episode rows",
            "whole-seed bootstrap metadata",
            "disjoint corrected-study seed blocks",
            "disjoint fit/calibration/holdout seeds",
            "zero right-censored directional examples",
        ],
    }, indent=2))


if __name__ == "__main__":
    main()
