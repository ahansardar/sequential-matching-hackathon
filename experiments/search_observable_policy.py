"""Search legal observable-only sequential matching policies.

This research runner never passes a world, seed or hidden member value into a
decision function. It searches fixed policy configurations on matched seeds.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import itertools
import json
import math
from pathlib import Path
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from adaptive import _pair_key, _safe_batch  # noqa: E402
from evaluate import VARIANTS, summarise  # noqa: E402
from kit import HARD, SOFT, Simulator, baseline_asks, eligibility, generate  # noqa: E402


PRIOR = {
    "response": (0.765, 4.0),
    "accept": (0.46, 4.0),
    "second": (0.23, 6.0),
}


def _logit(value):
    value = min(1 - 1e-6, max(1e-6, value))
    return math.log(value / (1 - value))


def _posterior(successes, trials, key, strength_scale):
    mean, strength = PRIOR[key]
    strength *= strength_scale
    return (successes + mean * strength) / (trials + strength)


def _histories(state):
    histories = {}

    def get(member_id):
        return histories.setdefault(member_id, {
            "response_trials": 0,
            "responses": 0,
            "accept_trials": 0,
            "accepts": 0,
            "second_trials": 0,
            "seconds": 0,
        })

    dates = {
        event["introduction_id"]: event.get("occurred_day")
        for event in state.get("feedback", [])
        if event.get("event") == "date_happened" and event.get("value") is True
    }
    for event in state.get("feedback", []):
        member_id = event.get("member_id")
        if not member_id:
            continue
        history = get(member_id)
        if event.get("event") == "introduction_response":
            history["response_trials"] += 1
            if event.get("value") is not None:
                history["responses"] += 1
                history["accept_trials"] += 1
                history["accepts"] += int(event.get("value") == "yes")
        elif event.get("event") == "second_meeting_intention" and event.get("introduction_id") in dates:
            history["second_trials"] += 1
            date_day = dates[event["introduction_id"]]
            history["seconds"] += int(
                event.get("value") == "yes"
                and event.get("occurred_day") is not None
                and event["occurred_day"] - date_day <= 3
            )
    return histories


def _member_quality(history, config, day):
    history = history or {}
    if day < config.get("history_start_day", 0):
        return 0.0
    scale = config["prior_scale"]
    response = _posterior(history.get("responses", 0), history.get("response_trials", 0), "response", scale)
    accept = _posterior(history.get("accepts", 0), history.get("accept_trials", 0), "accept", scale)
    second = _posterior(history.get("seconds", 0), history.get("second_trials", 0), "second", scale)
    trials = history.get("response_trials", 0)
    if trials < config.get("history_min_trials", 0):
        return 0.0
    if day < config.get("switch_day", -1):
        return config.get("early_exploration_weight", 0.0) / math.sqrt(1 + trials)
    return (
        config["response_weight"] * _logit(response)
        + config["accept_weight"] * _logit(accept)
        + config["second_weight"] * _logit(second)
        + config["exploration_weight"] / math.sqrt(1 + trials)
    )


def _edges(state, config):
    members = sorted(
        (
            member for member in state.get("members", [])
            if member.get("available")
            and all(member.get("fields", {}).get(field) is not None for field in HARD)
        ),
        key=lambda member: member["member_id"],
    )
    past = {
        _pair_key(item["user_a"], item["user_b"])
        for item in state.get("introductions", [])
    }
    histories = _histories(state)
    quality = {
        member["member_id"]: _member_quality(histories.get(member["member_id"]), config, state.get("day", 0))
        for member in members
    }
    edges = {}
    for left, right in itertools.combinations(members, 2):
        pair = _pair_key(left["member_id"], right["member_id"])
        if pair in past or eligibility(left, right)["status"] != "feasible":
            continue
        score = quality[pair[0]] + quality[pair[1]]
        for field, weight in zip(SOFT, config["soft_weights"]):
            left_value = left["fields"].get(field)
            right_value = right["fields"].get(field)
            if left_value is None or right_value is None:
                continue
            if left_value == right_value:
                score += weight
            elif config["signed_soft"]:
                score -= 0.5 * weight
        if score >= config["threshold"]:
            edges[pair] = score
    return edges


def _research_asks(state, config):
    mode = config.get("ask_mode", "baseline")
    if mode == "baseline":
        return baseline_asks(state)
    members = [member for member in state.get("members", []) if member.get("available")]
    # The public observation makes geographic fragmentation directly visible.
    # Sparse-only modes retain the baseline everywhere else.
    zones = {member.get("zone") for member in state.get("members", [])}
    if mode == "sparse_zone" and len(zones) < 8:
        return baseline_asks(state)
    candidates = [
        member for member in members
        if any(member.get("fields", {}).get(field) is None for field in HARD)
        and not any(member.get("field_status", {}).get(field) == "declined" for field in HARD)
    ]
    zone_sizes = {}
    for member in state.get("members", []):
        zone_sizes[member.get("zone")] = zone_sizes.get(member.get("zone"), 0) + 1
    known = [
        member for member in members
        if all(member.get("fields", {}).get(field) is not None for field in HARD)
    ]

    def possible_degree(candidate):
        return sum(
            other["member_id"] != candidate["member_id"]
            and eligibility(candidate, other)["status"] != "infeasible"
            for other in known
            if other.get("zone") == candidate.get("zone")
        )

    candidates.sort(key=lambda member: (
        -zone_sizes.get(member.get("zone"), 0),
        -possible_degree(member),
        member.get("arrived_day", 0),
        member["member_id"],
    ))
    return [
        {"member_id": member["member_id"], "field": "constraints"}
        for member in candidates[:state.get("ask_budget_remaining", 0) // 3]
    ]


def _configs():
    soft_sets = {
        "equal": [1, 1, 1, 1, 1, 1, 1],
        "funnel": [1.65, 0.47, 0.17, 0.25, 0, 0, 0],
        "accept": [0.70, 0.40, 0.25, 0.20, 0, 0, 0],
        "goal": [1, 0, 0, 0, 0, 0, 0],
    }
    history_sets = {
        "none": (0, 0, 0, 0),
        "light": (0.20, 0.20, 0, 0),
        "accept": (0.10, 0.50, 0, 0),
        "funnel": (0.20, 0.35, 0.15, 0),
        "explore": (0.15, 0.30, 0.10, 0.20),
        "exploit": (0.30, 0.65, 0.20, -0.10),
    }
    configs = []
    for soft_name, soft_weights in soft_sets.items():
        for history_name, weights in history_sets.items():
            response, accept, second, exploration = weights
            configs.append({
                "name": f"{soft_name}_{history_name}",
                "soft_weights": soft_weights,
                "signed_soft": soft_name != "equal",
                "response_weight": response,
                "accept_weight": accept,
                "second_weight": second,
                "exploration_weight": exploration,
                "prior_scale": 1.0,
                "threshold": -1e9,
                "ask_mode": "baseline",
            })
    # Waiting candidates use the strongest interpretable feature sets.
    for soft_name in ("equal", "funnel"):
        for threshold in (0.0, 0.5, 1.0, 1.5):
            base = next(item for item in configs if item["name"] == f"{soft_name}_funnel")
            config = dict(base)
            config["name"] = f"{soft_name}_funnel_wait_{threshold:g}"
            config["threshold"] = threshold
            configs.append(config)
    for source_name in ("equal_none", "equal_light", "equal_funnel"):
        source = next(item for item in configs if item["name"] == source_name)
        for ask_mode in ("sparse_zone", "zone"):
            config = dict(source)
            config["name"] = f"{source_name}_{ask_mode}"
            config["ask_mode"] = ask_mode
            configs.append(config)
    for switch_day in (15, 25, 35):
        for history_name, weights in {
            "light": (0.20, 0.20, 0.0),
            "exploit": (0.40, 0.70, 0.20),
        }.items():
            response, accept, second = weights
            source = next(item for item in configs if item["name"] == "equal_none")
            config = dict(source)
            config.update({
                "name": f"equal_two_phase_{history_name}_{switch_day}",
                "response_weight": response,
                "accept_weight": accept,
                "second_weight": second,
                "switch_day": switch_day,
                "early_exploration_weight": 3.0,
            })
            configs.append(config)
    lexicographic_sets = {
        "lex_equal_light": ([100, 100, 100, 100, 100, 100, 100], 1.0, 1.0, 0.0, 0),
        "lex_equal_mature": ([100, 100, 100, 100, 100, 100, 100], 1.0, 1.0, 0.0, 2),
        "lex_funnel_static": ([116, 105, 102, 103, 100, 100, 100], 0.0, 0.0, 0.0, 0),
        "lex_funnel_light": ([116, 105, 102, 103, 100, 100, 100], 1.0, 1.0, 0.0, 0),
        "lex_funnel_mature": ([116, 105, 102, 103, 100, 100, 100], 1.0, 1.0, 0.5, 2),
        "lex_funnel_accept": ([116, 105, 102, 103, 100, 100, 100], 0.5, 1.5, 0.0, 2),
    }
    for name, values in lexicographic_sets.items():
        soft_weights, response, accept, second, minimum_trials = values
        source = next(item for item in configs if item["name"] == "equal_none")
        config = dict(source)
        config.update({
            "name": name,
            "soft_weights": soft_weights,
            "response_weight": response,
            "accept_weight": accept,
            "second_weight": second,
            "history_min_trials": minimum_trials,
        })
        configs.append(config)
    for start_day in (10, 20, 30, 40):
        source = next(item for item in configs if item["name"] == "lex_equal_light")
        config = dict(source)
        config["name"] = f"lex_equal_light_start_{start_day}"
        config["history_start_day"] = start_day
        configs.append(config)
    return configs


def _episode(job):
    seed, variant, config = job
    simulator = Simulator(generate(seed, 200, "observable_search", variant))
    started = time.perf_counter()
    for _ in range(60):
        simulator.resolve_asks(_research_asks(simulator.observe(), config))
        edges = _edges(simulator.observe(), config)
        simulator.advance([list(pair) for pair in _safe_batch(edges)])
    arrived = {
        member["member_id"]
        for member in simulator.observe()["members"]
        if member["arrived_day"] <= 59
    }
    for _ in range(40):
        simulator.advance([])
    metrics = simulator.metrics()
    served = {
        member_id
        for introduction in simulator.introductions
        for member_id in (introduction["user_a"], introduction["user_b"])
    }
    metrics.update(
        valid=True,
        seed=seed,
        variant=variant,
        coverage=len(served) / max(1, len(arrived)),
        mutual_acceptances_per_100=100 * metrics["mutual_acceptances"] / max(1, len(arrived)),
        inference_seconds=time.perf_counter() - started,
    )
    return config["name"], metrics


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", default="3101,3102,3103")
    parser.add_argument("--variants", default="all")
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--names", default="all", help="Comma-separated configuration names, or all")
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "observable_search.json")
    args = parser.parse_args()
    seeds = [int(seed) for seed in args.seeds.split(",")]
    variants = VARIANTS if args.variants == "all" else tuple(args.variants.split(","))
    configs = _configs()
    if args.names != "all":
        requested = set(args.names.split(","))
        configs = [config for config in configs if config["name"] in requested]
        missing = requested - {config["name"] for config in configs}
        if missing:
            raise ValueError(f"Unknown configuration names: {sorted(missing)}")
    jobs = [(seed, variant, config) for config in configs for variant in variants for seed in seeds]
    rows = {config["name"]: [] for config in configs}
    with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as executor:
        for name, metrics in executor.map(_episode, jobs):
            rows[name].append(metrics)
    methods = {
        config["name"]: {
            "config": config,
            "summary": summarise(rows[config["name"]]),
        }
        for config in configs
    }
    ranking = sorted(
        methods,
        key=lambda name: methods[name]["summary"]["ranking_key_descending"],
        reverse=True,
    )
    result = {"seeds": seeds, "variants": variants, "ranking": ranking, "methods": methods}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    for name in ranking[:10]:
        summary = methods[name]["summary"]
        print(json.dumps({
            "name": name,
            "primary_score": summary["primary_score"],
            "coverage": summary["overall"]["coverage"],
            "mutual_acceptances": summary["overall"]["mutual_acceptances_per_100"],
        }))


if __name__ == "__main__":
    main()
