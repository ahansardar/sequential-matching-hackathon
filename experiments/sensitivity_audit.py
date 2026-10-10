"""Seed-level sensitivity checks for corrected paired comparisons."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import statistics


ROOT = Path(__file__).resolve().parents[1]
STUDIES = {
    "history": ("corrected_history_seed_grouped.json", "adaptive_legacy", "adaptive"),
    "guarded_allocation": ("corrected_allocation_outcomes.json", "adaptive_history_greedy", "adaptive"),
    "clarification_order": ("corrected_clarification_order.json", "adaptive", "adaptive_graph_asks"),
    "safe_cardinality_no_history": ("corrected_safe_cardinality_no_history.json", "adaptive_greedy", "adaptive_legacy"),
    "stable_member_order": ("corrected_member_order.json", "adaptive_input_order_greedy", "adaptive_greedy"),
    "equal_score_wait_tie": ("corrected_wait_tie.json", "adaptive_greedy", "adaptive_wait_tie_greedy"),
}
METRICS = ("msmi_per_100_arrived_members", "coverage")


def _episodes(payload, method):
    value = payload["methods"][method]
    return value["episodes"] if isinstance(value, dict) else value


def _paired_seed_deltas(payload, incumbent, challenger, metric):
    left = {(row["seed"], row["variant"]): row for row in _episodes(payload, incumbent)}
    right = {(row["seed"], row["variant"]): row for row in _episodes(payload, challenger)}
    if set(left) != set(right) or not left:
        raise ValueError("paired episodes are missing or misaligned")
    seeds = sorted({seed for seed, _ in left})
    variants = sorted({variant for _, variant in left})
    return {
        seed: statistics.mean(
            right[(seed, variant)][metric] - left[(seed, variant)][metric]
            for variant in variants
        )
        for seed in seeds
    }, variants


def exact_sign_flip_p_value(values):
    if not values or len(values) > 20:
        raise ValueError("exact sign-flip test supports 1 through 20 seed groups")
    observed = abs(statistics.mean(values))
    threshold = observed * len(values)
    extreme = 0
    total = 1 << len(values)
    signed_sum = sum(values)
    previous_gray = 0
    for index in range(total):
        if index:
            gray = index ^ (index >> 1)
            changed = gray ^ previous_gray
            bit = changed.bit_length() - 1
            signed_sum += (-2 if gray & changed else 2) * values[bit]
            previous_gray = gray
        extreme += abs(signed_sum) + 1e-15 >= threshold
    return extreme / total


def sensitivity(values):
    if len(values) < 2:
        raise ValueError("sensitivity analysis needs at least two seed groups")
    mean = statistics.mean(values)
    leave_one_out = [
        statistics.mean(values[:index] + values[index + 1:])
        for index in range(len(values))
    ]
    standard_deviation = statistics.stdev(values)
    return {
        "mean_difference": mean,
        "seed_group_standard_deviation": standard_deviation,
        "leave_one_seed_out_minimum": min(leave_one_out),
        "leave_one_seed_out_maximum": max(leave_one_out),
        "leave_one_seed_out_changes_sign": min(leave_one_out) < 0 < max(leave_one_out),
        "exact_two_sided_sign_flip_p_value": exact_sign_flip_p_value(values),
        "minimum_detectable_effect_80pct_approx": (
            (1.96 + 0.84) * standard_deviation / math.sqrt(len(values))
        ),
    }


def run(results_dir):
    output = {}
    for name, (filename, incumbent, challenger) in STUDIES.items():
        path = Path(results_dir) / filename
        if not path.exists():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        metrics = {}
        seed_count = None
        variant_count = None
        for metric in METRICS:
            by_seed, variants = _paired_seed_deltas(payload, incumbent, challenger, metric)
            metrics[metric] = sensitivity(list(by_seed.values()))
            seed_count = len(by_seed)
            variant_count = len(variants)
        output[name] = {
            "source": filename,
            "incumbent": incumbent,
            "challenger": challenger,
            "seed_groups": seed_count,
            "variants_per_seed": variant_count,
            "method": "paired seed-level scenario means; exact sign-flip and leave-one-seed-out checks",
            "metrics": metrics,
        }
    return {
        "status": "passed",
        "interpretation": "A challenger is not promoted from these checks alone. Sign instability or weak exact evidence reinforces an uncertain conclusion.",
        "studies": output,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", type=Path, default=ROOT / "results")
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "corrected_sensitivity.json")
    args = parser.parse_args()
    payload = run(args.results_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "studies": list(payload["studies"])}, indent=2))


if __name__ == "__main__":
    main()
