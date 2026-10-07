"""Build observable-only data for the local policy evaluation dashboard."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from adaptive import plan_asks, select_pairs  # noqa: E402
from kit import HARD, SOFT  # noqa: E402


RESULT_FILES = {
    "adaptive": "adaptive_101_103_all.json",
    "adaptive_always_max": "adaptive_always_max_101_103_all.json",
    "cavia": "cavia_101_103_all.json",
    "greedy": "greedy_101_103_all.json",
    "no_targeted_asks": "cavia_no_targeted_asks_101_103_all.json",
    "greedy_allocator": "cavia_greedy_101_103_all.json",
    "no_uncertainty": "cavia_no_uncertainty_101_103_all.json",
    "no_feedback": "cavia_no_feedback_101_103_all.json",
}


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def clean_member(member):
    fields = member.get("fields", {})
    statuses = member.get("field_status", {})
    return {
        "id": member["member_id"],
        "pool": member["pool_id"],
        "age": member["age"],
        "gender": member["gender"],
        "zone": member["zone"],
        "arrivalDay": member["arrived_day"],
        "available": bool(member.get("available", False)),
        "fields": {key: fields.get(key) for key in HARD + SOFT},
        "statuses": {key: statuses.get(key) for key in HARD + SOFT},
        "hardKnown": sum(fields.get(key) is not None for key in HARD),
        "hardTotal": len(HARD),
        "softKnown": sum(fields.get(key) is not None for key in SOFT),
        "softTotal": len(SOFT),
    }


def summarize_pool(pool_id, state):
    members = state["members"]
    known_hard = sum(sum(m.get("fields", {}).get(k) is not None for k in HARD) for m in members)
    known_soft = sum(sum(m.get("fields", {}).get(k) is not None for k in SOFT) for m in members)
    return {
        "id": pool_id,
        "day": state["day"],
        "members": len(members),
        "available": sum(bool(m.get("available")) for m in members),
        "introductions": len(state.get("introductions", [])),
        "feedback": len(state.get("feedback", [])),
        "hardObservedRate": known_hard / max(1, len(members) * len(HARD)),
        "softObservedRate": known_soft / max(1, len(members) * len(SOFT)),
    }


def build_pool_detail(pool_id, state):
    asks = plan_asks(state)
    selected_pairs, edges = select_pairs(state)
    selected = set(selected_pairs)
    by_id = {m["member_id"]: m for m in state["members"]}
    edge_rows = []
    for pair, score in sorted(edges.items(), key=lambda item: (-item[1], item[0])):
        left, right = pair
        edge_rows.append({
            "left": left,
            "right": right,
            "score": round(score, 4),
            "selected": pair in selected,
            "leftZone": by_id[left]["zone"],
            "rightZone": by_id[right]["zone"],
        })

    feedback_counts = {}
    for event in state.get("feedback", []):
        key = event["event"]
        feedback_counts[key] = feedback_counts.get(key, 0) + 1

    return {
        "id": pool_id,
        "day": state["day"],
        "askBudget": state["ask_budget_remaining"],
        "members": [clean_member(member) for member in state["members"]],
        "introductions": state.get("introductions", []),
        "feedbackCounts": feedback_counts,
        "asks": asks,
        "selectedPairs": [list(pair) for pair in sorted(selected)],
        "edges": edge_rows,
    }


def load_experiments(results_dir):
    methods = []
    raw_episodes = {}
    for method_id, filename in RESULT_FILES.items():
        path = results_dir / filename
        if not path.exists():
            continue
        payload = read_json(path)
        summary = payload["summary"]
        raw_episodes[path.stem] = [
            {key: row.get(key) for key in (
                "seed", "variant", "valid", "assignments", "mutual_acceptances",
                "dates", "mutual_second_meeting_intention", "missing_feedback",
                "ask_cost", "arrived_members", "served_members", "unserved_members",
                "coverage", "msmi_per_100_arrived_members", "mutual_acceptances_per_100",
                "inference_seconds",
            )}
            for row in payload.get("episodes", [])
        ]
        methods.append({
            "id": method_id,
            "label": {
                "adaptive": "Guarded-history policy",
                "adaptive_always_max": "Ablation · always maximum cardinality",
                "cavia": "CAVIA",
                "greedy": "Greedy baseline",
                "no_targeted_asks": "CAVIA · starter asks",
                "greedy_allocator": "CAVIA · greedy allocator",
                "no_uncertainty": "CAVIA · no uncertainty",
                "no_feedback": "CAVIA · no feedback",
            }[method_id],
            "source": filename,
            "episodes": len(payload.get("episodes", [])),
            "seeds": sorted({row["seed"] for row in payload.get("episodes", [])}),
            "primary": summary.get("primary_score"),
            "overall": summary.get("overall", {}),
            "scenarios": summary.get("scenario_means", {}),
            "valid": summary.get("eligible", False),
        })
    return methods, raw_episodes


def build(output):
    pool_summaries = []
    pool_details = {}
    for pool_dir in sorted((ROOT / "data").glob("public_*")):
        state = read_json(pool_dir / "state.json")
        pool_summaries.append(summarize_pool(pool_dir.name, state))
        pool_details[pool_dir.name] = build_pool_detail(pool_dir.name, state)

    experiments, raw_episodes = load_experiments(ROOT / "results")
    payload = {
        "meta": {
            "title": "Sequential Matching Data Viewer",
            "release": "1.0.0",
            "generatedFrom": "observable public snapshots and trusted local experiment outputs",
            "synthetic": True,
            "warning": "Synthetic simulator evidence only. Not real people or product performance.",
        },
        "pools": pool_summaries,
        "poolDetails": pool_details,
        "experiments": experiments,
        "rawEpisodes": raw_episodes,
        "scenarios": ["development", "sparse", "cold_start", "delayed", "shift", "drift"],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, separators=(",", ":"), allow_nan=False), encoding="utf-8")
    print(json.dumps({
        "output": str(output),
        "pools": len(pool_summaries),
        "members": sum(pool["members"] for pool in pool_summaries),
        "experiments": len(experiments),
        "bytes": output.stat().st_size,
    }, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "frontend" / "data" / "dashboard.json")
    args = parser.parse_args()
    build(args.output.resolve())


if __name__ == "__main__":
    main()
