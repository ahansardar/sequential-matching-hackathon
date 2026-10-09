"""Train auditable outcome models from declared synthetic rollout seeds.

This script collects labels only from feedback produced by valid introductions.
It never uses member truth, latent simulator attributes, member IDs as features,
or future feedback in an assignment-time feature snapshot.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import math
from pathlib import Path
import random
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from adaptive import _scored_edges  # noqa: E402
from evaluate import VARIANTS  # noqa: E402
from kit import Simulator, baseline_asks, generate  # noqa: E402
from outcome_model import (  # noqa: E402
    PAIR_FEATURES,
    comparison_features,
    feedback_history,
    pair_comparisons,
)


def _exploration_pairs(edges, seed, day):
    candidates = list(edges)
    random.Random(seed * 1000 + day).shuffle(candidates)
    selected = []
    used = set()
    for pair in candidates:
        if not used.intersection(pair):
            selected.append(pair)
            used.update(pair)
    return selected


def _history_snapshot(history):
    return {
        key: int(history.get(key, 0))
        for key in (
            "response_trials", "responses", "accept_trials", "accepts",
            "second_trials", "second_successes",
        )
    }


def collect_episode(seed, variant):
    simulator = Simulator(generate(seed, 200, "outcome_training", variant))
    snapshots = {}
    for day in range(60):
        simulator.resolve_asks(baseline_asks(simulator.observe()))
        state = simulator.observe()
        members = {member["member_id"]: member for member in state["members"]}
        histories = feedback_history(state)
        edges = _scored_edges(state)
        pairs = _exploration_pairs(edges, seed, day)
        previous_count = len(state["introductions"])
        simulator.advance([list(pair) for pair in pairs])
        new_introductions = simulator.observe()["introductions"][previous_count:]
        by_pair = {
            tuple(sorted((intro["user_a"], intro["user_b"]))): intro
            for intro in new_introductions
        }
        for pair in pairs:
            left, right = pair
            intro = by_pair[pair]
            snapshots[intro["introduction_id"]] = {
                "comparisons": pair_comparisons(members[left], members[right]),
                "left_history": _history_snapshot(histories.get(left, {})),
                "right_history": _history_snapshot(histories.get(right, {})),
                "assigned_day": day,
            }

    for _ in range(40):
        simulator.advance([])
    final_state = simulator.observe()
    events_by_intro = {}
    for event in final_state["feedback"]:
        events_by_intro.setdefault(event["introduction_id"], []).append(event)

    rows = []
    for introduction in final_state["introductions"]:
        intro_id = introduction["introduction_id"]
        snapshot = snapshots[intro_id]
        events = events_by_intro.get(intro_id, [])
        responses = {
            event["member_id"]: event
            for event in events
            if event["event"] == "introduction_response"
        }
        date_event = next(
            (event for event in events if event["event"] == "date_happened"),
            None,
        )
        seconds = {
            event["member_id"]: event
            for event in events
            if event["event"] == "second_meeting_intention"
        }
        member_ids = [introduction["user_a"], introduction["user_b"]]
        response_labels = []
        accept_labels = []
        second_labels = []
        for member_id in member_ids:
            response = responses.get(member_id)
            response_labels.append(int(response is not None and response.get("value") is not None))
            accept_labels.append(
                None if response is None or response.get("value") is None
                else int(response.get("value") == "yes")
            )
            second = seconds.get(member_id)
            second_labels.append(
                None if date_event is None or date_event.get("value") is not True
                else int(
                    second is not None
                    and second.get("value") == "yes"
                    and second.get("occurred_day") is not None
                    and second["occurred_day"] - date_event["occurred_day"] <= 3
                )
            )
        date_within_30 = (
            date_event is not None
            and date_event.get("value") is True
            and date_event["occurred_day"] - introduction["assigned_day"] <= 30
        )
        msmi = (
            date_within_30
            and all(label == 1 for label in second_labels)
        )
        rows.append({
            **snapshot,
            "response_labels": response_labels,
            "accept_labels": accept_labels,
            "date_observed": date_event is not None,
            "date_within_30": int(date_within_30),
            "second_labels": second_labels,
            "msmi": int(msmi),
        })
    return rows


def _collect_job(job):
    seed, variant = job
    return seed, variant, collect_episode(seed, variant)


def _mean(rows, key):
    values = [value for row in rows for value in row[key] if value is not None]
    return sum(values) / len(values)


def _posterior(successes, trials, mean, strength):
    return (successes + mean * strength) / (trials + strength)


def _logit(value):
    value = min(1 - 1e-6, max(1e-6, value))
    return math.log(value / (1 - value))


def _history_rates(history, priors):
    return {
        "response": _posterior(history["responses"], history["response_trials"], priors["response_mean"], priors["response_strength"]),
        "accept": _posterior(history["accepts"], history["accept_trials"], priors["accept_mean"], priors["accept_strength"]),
        "second": _posterior(history["second_successes"], history["second_trials"], priors["second_mean"], priors["second_strength"]),
    }


def _fit_logistic(examples, feature_names, l2=0.002, iterations=240, balanced=False):
    prevalence = min(1 - 1e-5, max(1e-5, sum(label for _, label in examples) / len(examples)))
    weights = [0.0 if balanced else _logit(prevalence)] + [0.0] * len(feature_names)
    positive_count = sum(label for _, label in examples)
    negative_count = len(examples) - positive_count
    prepared = []
    for values, label in examples:
        sample_weight = (
            0.5 / (positive_count if label else negative_count)
            if balanced
            else 1 / len(examples)
        )
        prepared.append((
            [1.0] + [values.get(name, 0.0) for name in feature_names],
            label,
            sample_weight,
        ))
    for iteration in range(iterations):
        gradient = [0.0] * len(weights)
        for values, label, sample_weight in prepared:
            linear = sum(weight * value for weight, value in zip(weights, values))
            probability = 1 / (1 + math.exp(-max(-30.0, min(30.0, linear))))
            error = sample_weight * (probability - label)
            for index, value in enumerate(values):
                gradient[index] += error * value
        rate = 0.35 / math.sqrt(1 + iteration / 80)
        for index in range(len(weights)):
            regularisation = 0.0 if index == 0 else l2 * weights[index]
            weights[index] -= rate * (gradient[index] + regularisation)
    if balanced:
        weights[0] += _logit(prevalence)
    return {
        "intercept": weights[0],
        "coefficients": dict(zip(feature_names, weights[1:])),
        "training_examples": len(examples),
        "positive_rate": prevalence,
    }


def train(rows, seeds, variants, history_strength=4.0):
    response_mean = _mean(rows, "response_labels")
    accept_mean = _mean(rows, "accept_labels")
    second_mean = _mean(rows, "second_labels")
    priors = {
        "response_mean": response_mean,
        "response_strength": history_strength,
        "accept_mean": accept_mean,
        "accept_strength": history_strength,
        "second_mean": second_mean,
        "second_strength": history_strength,
    }
    static_examples = []
    history_examples = []
    acceptance_examples = []
    second_examples = []
    for row in rows:
        pair_values = comparison_features(row["comparisons"])
        rates = [
            _history_rates(row["left_history"], priors),
            _history_rates(row["right_history"], priors),
        ]
        static_examples.append((pair_values, row["msmi"]))
        history_values = dict(pair_values)
        history_values.update({
            "response_logit_sum": sum(_logit(rate["response"]) for rate in rates),
            "accept_logit_sum": sum(_logit(rate["accept"]) for rate in rates),
            "second_logit_sum": sum(_logit(rate["second"]) for rate in rates),
        })
        history_examples.append((history_values, row["msmi"]))
        for index, label in enumerate(row["accept_labels"]):
            if label is not None:
                acceptance_examples.append((
                    dict(pair_values, accept_history_logit=_logit(rates[index]["accept"])),
                    label,
                ))
        for index, label in enumerate(row["second_labels"]):
            if label is not None:
                second_examples.append((
                    dict(pair_values, second_history_logit=_logit(rates[index]["second"])),
                    label,
                ))

    accepted_pairs = [row for row in rows if row["date_observed"]]
    date_probability = sum(row["date_within_30"] for row in accepted_pairs) / len(accepted_pairs)
    history_names = PAIR_FEATURES + (
        "response_logit_sum", "accept_logit_sum", "second_logit_sum",
    )
    return {
        "schema_version": "1.0.0",
        "target": "mutual_second_meeting_intention_within_contract_window",
        "training": {
            "source": "valid observable-feedback rollouts from the public synthetic generator",
            "seeds": seeds,
            "variants": variants,
            "episodes": len(seeds) * len(variants),
            "introductions": len(rows),
            "feature_policy": "assignment-time public observations only",
        },
        "priors": priors,
        "date_within_30_probability": date_probability,
        "models": {
            "learned_static": _fit_logistic(static_examples, PAIR_FEATURES, balanced=True),
            "learned_history": _fit_logistic(history_examples, history_names, balanced=True),
            "acceptance": _fit_logistic(acceptance_examples, PAIR_FEATURES + ("accept_history_logit",)),
            "second": _fit_logistic(second_examples, PAIR_FEATURES + ("second_history_logit",)),
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", default="2001-2040")
    parser.add_argument("--variants", default="all")
    parser.add_argument("--history-strength", type=float, default=4.0)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--cache", type=Path, default=ROOT / "results" / "outcome_training_rows.json")
    parser.add_argument("--input-cache", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "outcome_model.json")
    args = parser.parse_args()
    if "-" in args.seeds and "," not in args.seeds:
        start, end = (int(value) for value in args.seeds.split("-"))
        seeds = list(range(start, end + 1))
    else:
        seeds = [int(value) for value in args.seeds.split(",")]
    variants = list(VARIANTS) if args.variants == "all" else args.variants.split(",")
    if args.input_cache:
        cached = json.loads(args.input_cache.read_text(encoding="utf-8"))
        rows = cached["rows"]
        if cached["seeds"] != seeds or cached["variants"] != variants:
            raise ValueError("cache seeds or variants do not match requested training split")
    else:
        rows = []
        jobs = [(seed, variant) for variant in variants for seed in seeds]
        if args.workers > 1:
            with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as executor:
                collected = executor.map(_collect_job, jobs)
                for seed, variant, episode_rows in collected:
                    rows.extend(episode_rows)
                    print(json.dumps({"seed": seed, "variant": variant, "introductions": len(episode_rows)}), flush=True)
        else:
            for job in jobs:
                seed, variant, episode_rows = _collect_job(job)
                rows.extend(episode_rows)
                print(json.dumps({"seed": seed, "variant": variant, "introductions": len(episode_rows)}), flush=True)
        args.cache.parent.mkdir(parents=True, exist_ok=True)
        args.cache.write_text(
            json.dumps({"seeds": seeds, "variants": variants, "rows": rows}),
            encoding="utf-8",
        )
        print(json.dumps({"cache": str(args.cache), "rows": len(rows)}), flush=True)
    model = train(rows, seeds, variants, args.history_strength)
    args.output.write_text(json.dumps(model, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(args.output),
        "episodes": model["training"]["episodes"],
        "introductions": model["training"]["introductions"],
        "response_mean": model["priors"]["response_mean"],
        "accept_mean": model["priors"]["accept_mean"],
        "second_mean": model["priors"]["second_mean"],
        "date_within_30_probability": model["date_within_30_probability"],
    }, indent=2))


if __name__ == "__main__":
    main()
