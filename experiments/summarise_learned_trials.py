"""Build the machine-readable learned-policy selection summary."""
from __future__ import annotations

import json
import math
from pathlib import Path
import statistics


ROOT = Path(__file__).resolve().parents[1]
TRIALS = (
    ("tuning_screen", "learned_screen_2101_2110.json", "learned_static", "adaptive"),
    ("tuning_screen_history", "learned_screen_2101_2110.json", "learned_history", "adaptive"),
    ("history_holdout", "learned_holdout_2201_2220.json", "learned_history", "adaptive"),
    ("static_holdout", "learned_static_holdout_2301_2320.json", "learned_static", "adaptive"),
    ("static_confirmation", "learned_static_confirm_2401_2420.json", "learned_static", "adaptive"),
)


def analyse(path, challenger, baseline):
    payload = json.loads(path.read_text(encoding="utf-8"))
    challenger_rows = payload["methods"][challenger]["episodes"]
    baseline_rows = payload["methods"][baseline]["episodes"]
    key = lambda row: (row["variant"], row["seed"])
    challenger_by_key = {key(row): row for row in challenger_rows}
    baseline_by_key = {key(row): row for row in baseline_rows}
    if challenger_by_key.keys() != baseline_by_key.keys():
        raise ValueError(f"unmatched episodes in {path}")
    differences = []
    outcomes = {challenger: 0, baseline: 0}
    scenario_differences = {}
    wins = ties = losses = 0
    for episode_key in sorted(challenger_by_key):
        challenger_row = challenger_by_key[episode_key]
        baseline_row = baseline_by_key[episode_key]
        difference = (
            challenger_row["msmi_per_100_arrived_members"]
            - baseline_row["msmi_per_100_arrived_members"]
        )
        differences.append(difference)
        scenario_differences.setdefault(episode_key[0], []).append(difference)
        outcomes[challenger] += challenger_row["mutual_second_meeting_intention"]
        outcomes[baseline] += baseline_row["mutual_second_meeting_intention"]
        wins += difference > 0
        ties += difference == 0
        losses += difference < 0
    mean = statistics.fmean(differences)
    standard_error = statistics.stdev(differences) / math.sqrt(len(differences))
    return {
        "episodes": len(differences),
        "challenger": challenger,
        "baseline": baseline,
        "challenger_primary_score": payload["methods"][challenger]["summary"]["primary_score"],
        "baseline_primary_score": payload["methods"][baseline]["summary"]["primary_score"],
        "paired_primary_delta": mean,
        "paired_normal_95_percent_interval": [mean - 1.96 * standard_error, mean + 1.96 * standard_error],
        "challenger_total_msmi": outcomes[challenger],
        "baseline_total_msmi": outcomes[baseline],
        "paired_wins": wins,
        "paired_ties": ties,
        "paired_losses": losses,
        "scenario_primary_deltas": {
            scenario: statistics.fmean(values)
            for scenario, values in sorted(scenario_differences.items())
        },
    }


def main():
    results_dir = ROOT / "results"
    model = json.loads((ROOT / "outcome_model.json").read_text(encoding="utf-8"))
    summary = {
        "decision": "retain_safe_cardinality",
        "reason": "learned candidates did not improve every untouched confirmation block",
        "training": model["training"],
        "trials": {
            name: analyse(results_dir / filename, challenger, baseline)
            for name, filename, challenger, baseline in TRIALS
        },
    }
    output = results_dir / "learned_model_selection_summary.json"
    output.write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "decision": summary["decision"]}, indent=2))


if __name__ == "__main__":
    main()
