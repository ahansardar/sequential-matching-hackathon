"""Compare one policy component at a time on matched seed groups.

This runner is research-only. It uses the public simulator in-process and keeps
all six variants from one generated seed together in the uncertainty analysis.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
from pathlib import Path
import statistics
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluate import VARIANTS, summarise  # noqa: E402
from experiments.compare_policies import direct_episode  # noqa: E402
from experiments.confidence_audit import paired_analysis  # noqa: E402


METRICS = (
    "msmi_per_100_arrived_members",
    "assignments",
    "mutual_acceptances",
    "dates",
    "coverage",
    "unserved_members",
    "ask_cost",
    "median_first_wait_days",
    "p90_first_wait_days",
)


def _percentile(values, probability):
    if not values:
        return None
    ordered = sorted(values)
    position = probability * (len(ordered) - 1)
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def _run_job(job):
    row = direct_episode(*job)
    waits = row["first_introduction_wait_days"]
    row["median_first_wait_days"] = statistics.median(waits) if waits else None
    row["p90_first_wait_days"] = _percentile(waits, 0.90)
    return row


def run_comparison(incumbent, challenger, seeds, variants, workers, resamples, bootstrap_seed):
    rows = {}
    for method in (incumbent, challenger):
        jobs = [(seed, variant, method) for variant in variants for seed in seeds]
        if workers > 1:
            with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as executor:
                method_rows = list(executor.map(_run_job, jobs))
        else:
            method_rows = [_run_job(job) for job in jobs]
        rows[method] = method_rows

    analyses = {}
    for metric in METRICS:
        if any(row[metric] is None for method_rows in rows.values() for row in method_rows):
            continue
        analyses[metric] = paired_analysis(
            rows[incumbent],
            rows[challenger],
            resamples=resamples,
            seed=bootstrap_seed,
            metric=metric,
        )
    return {
        "trusted_in_process": True,
        "comparison_design": {
            "incumbent": incumbent,
            "challenger": challenger,
            "paired_by": ["seed", "variant"],
            "bootstrap_cluster": "seed with every variant kept together",
            "scenario_weighting": "equal",
            "seeds": seeds,
            "variants": variants,
        },
        "methods": {
            method: {"episodes": method_rows, "summary": summarise(method_rows)}
            for method, method_rows in rows.items()
        },
        "paired_metrics": analyses,
    }


def _parse_seeds(value):
    if "-" in value and "," not in value:
        start, end = (int(part) for part in value.split("-"))
        return list(range(start, end + 1))
    return [int(part) for part in value.split(",")]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--incumbent", required=True)
    parser.add_argument("--challenger", required=True)
    parser.add_argument("--seeds", required=True)
    parser.add_argument("--variants", default="all")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--resamples", type=int, default=20000)
    parser.add_argument("--bootstrap-seed", type=int, default=1701)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    seeds = _parse_seeds(args.seeds)
    variants = list(VARIANTS) if args.variants == "all" else args.variants.split(",")
    if not seeds or not variants or any(variant not in VARIANTS for variant in variants):
        parser.error("Choose at least one seed and recognized variant")
    payload = run_comparison(
        args.incumbent,
        args.challenger,
        seeds,
        variants,
        args.workers,
        args.resamples,
        args.bootstrap_seed,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(args.output),
        "incumbent": payload["methods"][args.incumbent]["summary"],
        "challenger": payload["methods"][args.challenger]["summary"],
        "paired_metrics": payload["paired_metrics"],
    }, indent=2))


if __name__ == "__main__":
    main()
