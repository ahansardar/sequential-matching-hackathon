"""Measure real subprocess latency and protocol sizes for one public episode."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import statistics
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluate import VARIANTS, invoke  # noqa: E402
from kit import Simulator, VERSION, generate  # noqa: E402


def percentile(values, fraction):
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int((len(ordered) - 1) * fraction))]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", default="adaptive")
    parser.add_argument("--seed", type=int, default=101)
    parser.add_argument("--variant", choices=VARIANTS, default="development")
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "adaptive_benchmark.json")
    args = parser.parse_args()

    simulator = Simulator(generate(args.seed, 200, "benchmark", args.variant))
    command = [sys.executable, str(ROOT / "policy.py"), "--baseline", args.baseline]
    memory = None
    timings = []
    request_sizes = []
    response_sizes = []
    for _ in range(60):
        for phase in ("ask", "match"):
            request = {
                "schema_version": VERSION,
                "phase": phase,
                "state": simulator.observe(),
                "memory": memory,
            }
            response, elapsed = invoke(command, request)
            timings.append(elapsed)
            request_sizes.append(len(json.dumps(request, allow_nan=False).encode()))
            response_sizes.append(len(json.dumps(response, allow_nan=False).encode()))
            memory = response["memory"]
            if phase == "ask":
                simulator.resolve_asks(response["asks"])
            else:
                simulator.advance(response["pairs"])

    payload = {
        "baseline": args.baseline,
        "seed": args.seed,
        "variant": args.variant,
        "calls": len(timings),
        "latency_seconds": {
            "mean": statistics.mean(timings),
            "p95": percentile(timings, 0.95),
            "maximum": max(timings),
            "limit": 10.0,
        },
        "protocol_bytes": {
            "maximum_request": max(request_sizes),
            "maximum_response": max(response_sizes),
            "limit": 1024 * 1024,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
