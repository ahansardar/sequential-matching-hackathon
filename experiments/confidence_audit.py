"""Run a paired policy comparison with a seed-clustered bootstrap interval."""
from __future__ import annotations

import argparse
import concurrent.futures
import json
from pathlib import Path
import random
import statistics
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluate import VARIANTS, summarise  # noqa: E402
from experiments.compare_policies import direct_episode  # noqa: E402


def _run_job(job):
    return direct_episode(*job)


def _percentile(values, probability):
    ordered = sorted(values)
    position = probability * (len(ordered) - 1)
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def paired_analysis(
    incumbent_rows,
    challenger_rows,
    resamples=10000,
    seed=1701,
    metric="msmi_per_100_arrived_members",
):
    if resamples < 1:
        raise ValueError("resamples must be positive")
    if not incumbent_rows or not challenger_rows:
        raise ValueError("Policies must contain at least one paired episode")
    key = lambda row: (row["variant"], row["seed"])
    incumbent = {key(row): row for row in incumbent_rows}
    challenger = {key(row): row for row in challenger_rows}
    if len(incumbent) != len(incumbent_rows) or len(challenger) != len(challenger_rows):
        raise ValueError("Policies must not contain duplicate variant and seed rows")
    if incumbent.keys() != challenger.keys():
        raise ValueError("Policies must have identical variant and seed rows")
    deltas = {
        pair: challenger[pair][metric] - incumbent[pair][metric]
        for pair in incumbent
    }
    variants = sorted({variant for variant, _ in deltas})
    seeds = sorted({episode_seed for _, episode_seed in deltas})
    expected = {(variant, episode_seed) for variant in variants for episode_seed in seeds}
    if set(deltas) != expected:
        raise ValueError(
            "Every seed group must contain the same complete set of variants"
        )
    by_variant = {
        variant: [deltas[(variant, episode_seed)] for episode_seed in seeds]
        for variant in variants
    }
    generator = random.Random(seed)
    bootstrap = []
    for _ in range(resamples):
        # A generated seed defines one world under all scenario variants. Sample
        # that whole six-variant group together so correlated worlds never count
        # as independent observations.
        sampled_seeds = [generator.choice(seeds) for _ in seeds]
        family_means = [
            statistics.mean(deltas[(variant, episode_seed)] for episode_seed in sampled_seeds)
            for variant in variants
        ]
        bootstrap.append(statistics.mean(family_means))
    return {
        "metric": metric,
        "paired_episodes": len(deltas),
        "seed_groups": len(seeds),
        "variants_per_seed": len(variants),
        "mean_primary_delta": statistics.mean(
            statistics.mean(values) for values in by_variant.values()
        ),
        "scenario_mean_deltas": {
            variant: statistics.mean(values)
            for variant, values in by_variant.items()
        },
        "bootstrap": {
            "method": "paired percentile bootstrap clustered by seed",
            "resampling_unit": "whole seed group with every scenario variant",
            "scenario_weighting": "equal weight after within-variant seed means",
            "resamples": resamples,
            "seed": seed,
            "confidence_level": 0.95,
            "lower": _percentile(bootstrap, 0.025),
            "upper": _percentile(bootstrap, 0.975),
        },
    }


def promotion_gate(incumbent_summary, challenger_summary, analysis):
    scenario_deltas = analysis["scenario_mean_deltas"]
    checks = {
        "both_eligible": bool(
            incumbent_summary.get("eligible") and challenger_summary.get("eligible")
        ),
        "primary_score_improved": (
            challenger_summary.get("primary_score", float("-inf"))
            > incumbent_summary.get("primary_score", float("-inf"))
        ),
        "confidence_interval_above_zero": analysis["bootstrap"]["lower"] > 0.0,
        "no_scenario_mean_loss": all(delta >= 0.0 for delta in scenario_deltas.values()),
    }
    return {
        "promote": all(checks.values()),
        "checks": checks,
    }


def _parse_seeds(value):
    if "-" in value and "," not in value:
        start, end = (int(part) for part in value.split("-"))
        if end < start:
            raise ValueError("seed range end must not be below its start")
        return list(range(start, end + 1))
    return [int(part) for part in value.split(",")]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--incumbent", default="adaptive")
    parser.add_argument("--challenger", default="adaptive_precise")
    parser.add_argument("--seeds", required=True, help="Comma-separated integer seeds")
    parser.add_argument("--variants", default="all")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--resamples", type=int, default=10000)
    parser.add_argument("--bootstrap-seed", type=int, default=1701)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "results" / "confidence_audit.json",
    )
    args = parser.parse_args()
    try:
        seeds = _parse_seeds(args.seeds)
    except ValueError as error:
        parser.error(str(error))
    variants = list(VARIANTS) if args.variants == "all" else args.variants.split(",")
    if not seeds or not variants or any(variant not in VARIANTS for variant in variants):
        parser.error("Choose at least one seed and recognized variant")

    rows = {}
    jobs = [
        (seed, variant, method)
        for method in (args.incumbent, args.challenger)
        for variant in variants
        for seed in seeds
    ]
    if args.workers > 1:
        with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as executor:
            completed = list(executor.map(_run_job, jobs))
    else:
        completed = [_run_job(job) for job in jobs]
    per_method = len(seeds) * len(variants)
    rows[args.incumbent] = completed[:per_method]
    rows[args.challenger] = completed[per_method:]

    method_results = {
        method: {"episodes": method_rows, "summary": summarise(method_rows)}
        for method, method_rows in rows.items()
    }
    analysis = paired_analysis(
        rows[args.incumbent],
        rows[args.challenger],
        resamples=args.resamples,
        seed=args.bootstrap_seed,
    )
    payload = {
        "trusted_in_process": True,
        "incumbent": args.incumbent,
        "challenger": args.challenger,
        "methods": method_results,
        "paired_analysis": analysis,
        "promotion_gate": promotion_gate(
            method_results[args.incumbent]["summary"],
            method_results[args.challenger]["summary"],
            analysis,
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "incumbent": payload["methods"][args.incumbent]["summary"],
        "challenger": payload["methods"][args.challenger]["summary"],
        "paired_analysis": payload["paired_analysis"],
        "promotion_gate": payload["promotion_gate"],
    }, indent=2))


if __name__ == "__main__":
    main()
