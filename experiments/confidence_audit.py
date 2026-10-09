"""Run a paired policy comparison with a stratified bootstrap interval."""
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


def paired_analysis(incumbent_rows, challenger_rows, resamples=10000, seed=1701):
    if resamples < 1:
        raise ValueError("resamples must be positive")
    key = lambda row: (row["variant"], row["seed"])
    incumbent = {key(row): row for row in incumbent_rows}
    challenger = {key(row): row for row in challenger_rows}
    if incumbent.keys() != challenger.keys():
        raise ValueError("Policies must have identical variant and seed rows")
    deltas = {
        pair: challenger[pair]["msmi_per_100_arrived_members"]
        - incumbent[pair]["msmi_per_100_arrived_members"]
        for pair in incumbent
    }
    by_variant = {
        variant: [value for (name, _), value in deltas.items() if name == variant]
        for variant in sorted({variant for variant, _ in deltas})
    }
    generator = random.Random(seed)
    bootstrap = []
    for _ in range(resamples):
        family_means = []
        for values in by_variant.values():
            sample = [generator.choice(values) for _ in values]
            family_means.append(statistics.mean(sample))
        bootstrap.append(statistics.mean(family_means))
    return {
        "paired_episodes": len(deltas),
        "mean_primary_delta": statistics.mean(
            statistics.mean(values) for values in by_variant.values()
        ),
        "scenario_mean_deltas": {
            variant: statistics.mean(values)
            for variant, values in by_variant.items()
        },
        "bootstrap": {
            "method": "paired stratified percentile",
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
    seeds = [int(value) for value in args.seeds.split(",")]
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
