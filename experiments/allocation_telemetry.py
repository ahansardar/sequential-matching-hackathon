"""Measure how often guarded global allocation changes the daily batch."""
from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from adaptive import (  # noqa: E402
    _greedy_pairs,
    _maximum_quality_batch,
    _scored_edges,
    decide,
)
from evaluate import VARIANTS  # noqa: E402
from kit import Simulator, generate  # noqa: E402


def episode_telemetry(seed, variant):
    simulator = Simulator(generate(seed, 200, "allocation_telemetry", variant))
    memory = None
    counts = collections.Counter()
    for _ in range(60):
        ask = decide({
            "phase": "ask",
            "state": simulator.observe(),
            "memory": memory,
        })
        simulator.resolve_asks(ask["asks"])
        state = simulator.observe()
        edges = _scored_edges(state)
        greedy = _greedy_pairs(edges)
        maximum = _maximum_quality_batch(edges)
        accepted = (
            len(maximum) > len(greedy)
            and sum(edges[pair] for pair in maximum) + 1e-12
            >= sum(edges[pair] for pair in greedy)
        )
        match = decide({"phase": "match", "state": state, "memory": ask["memory"]})
        expected = maximum if accepted else greedy
        if match["pairs"] != [list(pair) for pair in expected]:
            raise AssertionError("Telemetry path differs from the submitted policy")
        counts["days"] += 1
        counts["nonempty_days"] += bool(edges)
        counts["cardinality_gain_days"] += len(maximum) > len(greedy)
        counts["global_used_days"] += accepted
        simulator.advance(match["pairs"])
        memory = match["memory"]
    return dict(counts)


def summarise(rows):
    total = collections.Counter()
    for row in rows:
        total.update(row["counts"])
    days = total["days"]
    nonempty = total["nonempty_days"]
    result = dict(total)
    result["global_rate_all_days"] = total["global_used_days"] / max(1, days)
    result["global_rate_nonempty_days"] = (
        total["global_used_days"] / max(1, nonempty)
    )
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", required=True, help="Comma-separated integer seeds")
    parser.add_argument("--variants", default="all")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "results" / "allocation_telemetry.json",
    )
    args = parser.parse_args()
    seeds = [int(value) for value in args.seeds.split(",")]
    variants = list(VARIANTS) if args.variants == "all" else args.variants.split(",")
    if not seeds or not variants or any(variant not in VARIANTS for variant in variants):
        parser.error("Choose at least one seed and recognized variant")

    rows = []
    for variant in variants:
        for seed in seeds:
            rows.append({
                "seed": seed,
                "variant": variant,
                "counts": episode_telemetry(seed, variant),
            })
    by_variant = {
        variant: summarise([row for row in rows if row["variant"] == variant])
        for variant in variants
    }
    payload = {
        "policy": "adaptive",
        "seeds": seeds,
        "variants": variants,
        "episodes": len(rows),
        "overall": summarise(rows),
        "by_variant": by_variant,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
