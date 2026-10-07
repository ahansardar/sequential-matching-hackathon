"""Fast, trusted research runner for matched policy comparisons.

This script calls policy functions in-process to make iteration practical. It
passes only simulator observations to the policy. Final evidence must still be
regenerated with evaluate.py and the offline container.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
from pathlib import Path
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluate import VARIANTS, summarise  # noqa: E402
from kit import Simulator, generate  # noqa: E402
from policy import decide  # noqa: E402


def research_decide(request, mode):
    if mode in {"adaptive_precise", "adaptive_raw_guard"}:
        from experiments.precise_policy import decide as decide_precise
        return decide_precise(request, mode)
    return decide(request, "adaptive_greedy" if mode == "greedy_fast" else mode)


def direct_episode(seed, variant, mode):
    simulator = Simulator(generate(seed, 200, "evaluation", variant))
    memory = None
    started = time.perf_counter()
    for _ in range(60):
        ask = research_decide({"phase": "ask", "state": simulator.observe(), "memory": memory}, mode)
        simulator.resolve_asks(ask["asks"])
        match = research_decide({"phase": "match", "state": simulator.observe(), "memory": ask["memory"]}, mode)
        simulator.advance(match["pairs"])
        memory = match["memory"]

    arrived = {
        member["member_id"]: member["arrived_day"]
        for member in simulator.observe()["members"]
        if member["arrived_day"] <= 59
    }
    for _ in range(40):
        simulator.advance([])
    result = simulator.metrics()
    first = {}
    for introduction in simulator.introductions:
        for member_id in (introduction["user_a"], introduction["user_b"]):
            first.setdefault(member_id, introduction["assigned_day"])
    result.update(
        valid=True,
        seed=seed,
        variant=variant,
        arrived_members=len(arrived),
        served_members=len(first),
        unserved_members=len(arrived) - len(first),
        coverage=len(first) / max(1, len(arrived)),
        mutual_acceptances_per_100=100 * result["mutual_acceptances"] / max(1, len(arrived)),
        first_introduction_wait_days=sorted(first[member_id] - arrived[member_id] for member_id in first),
        inference_seconds=time.perf_counter() - started,
    )
    return result


def _run_job(job):
    """Top-level adapter so Windows worker processes can pickle the job."""
    return direct_episode(*job)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--methods", default="adaptive,greedy,cavia")
    parser.add_argument("--seeds", default="101,102,103")
    parser.add_argument("--variants", default="all")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "research_comparison.json")
    args = parser.parse_args()
    methods = args.methods.split(",")
    seeds = [int(seed) for seed in args.seeds.split(",")]
    variants = list(VARIANTS) if args.variants == "all" else args.variants.split(",")

    payload = {"trusted_in_process": True, "methods": {}}
    for method in methods:
        jobs = [(seed, variant, method) for variant in variants for seed in seeds]
        if args.workers > 1:
            with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as executor:
                rows = list(executor.map(_run_job, jobs))
        else:
            rows = [direct_episode(*job) for job in jobs]
        for row in rows:
            print(json.dumps({
                "method": method,
                "variant": row["variant"],
                "seed": row["seed"],
                "msmi": row["mutual_second_meeting_intention"],
                "coverage": row["coverage"],
            }), flush=True)
        payload["methods"][method] = {"episodes": rows, "summary": summarise(rows)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({method: data["summary"] for method, data in payload["methods"].items()}, indent=2))


if __name__ == "__main__":
    main()
