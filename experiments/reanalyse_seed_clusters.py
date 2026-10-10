"""Recompute a saved matched comparison with whole-seed bootstrap clusters."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.confidence_audit import paired_analysis, promotion_gate  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--resamples", type=int, default=20000)
    parser.add_argument("--bootstrap-seed", type=int, default=1701)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = json.loads(args.input.read_text(encoding="utf-8"))
    incumbent = source["incumbent"]
    challenger = source["challenger"]
    incumbent_rows = source["methods"][incumbent]["episodes"]
    challenger_rows = source["methods"][challenger]["episodes"]
    analysis = paired_analysis(
        incumbent_rows,
        challenger_rows,
        resamples=args.resamples,
        seed=args.bootstrap_seed,
    )
    payload = {
        "source_result": str(args.input.as_posix()),
        "incumbent": incumbent,
        "challenger": challenger,
        "methods": source["methods"],
        "paired_analysis": analysis,
        "promotion_gate": promotion_gate(
            source["methods"][incumbent]["summary"],
            source["methods"][challenger]["summary"],
            analysis,
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(args.output),
        "paired_analysis": analysis,
        "promotion_gate": payload["promotion_gate"],
    }, indent=2))


if __name__ == "__main__":
    main()
