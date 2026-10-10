"""Fit and evaluate directional response probabilities on untouched seed groups.

The estimator is a report diagnostic, not a ranking score and not part of the
submission runtime. Features are captured from the public observation before
each assignment. Labels are read only after the response deadline has matured.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import math
from pathlib import Path
import random
import statistics
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from adaptive import _feedback_history  # noqa: E402
from evaluate import VARIANTS  # noqa: E402
from kit import SOFT, Simulator, eligibility, generate  # noqa: E402
from outcome_model import comparison_features, pair_comparisons  # noqa: E402
from policy import decide  # noqa: E402
from experiments.train_outcome_model import _fit_logistic  # noqa: E402
from experiments.outcome_events import recorded_yes_by_deadline  # noqa: E402


TARGET_A = "user_a_recorded_yes_by_response_deadline"
TARGET_B = "user_b_recorded_yes_by_response_deadline"
HISTORY_STRENGTH = 4.0


def _logit(value):
    value = min(1 - 1e-6, max(1e-6, value))
    return math.log(value / (1 - value))


def _sigmoid(value):
    value = max(-30.0, min(30.0, value))
    return 1 / (1 + math.exp(-value))


def _history_snapshot(histories, member_id):
    history = histories.get(member_id, {})
    return {
        "response_trials": int(history.get("response_trials", 0)),
        "responses": int(history.get("responses", 0)),
        "yeses": int(history.get("accepts", 0)),
    }


def _base_features(actor, other):
    values = comparison_features(pair_comparisons(actor, other))
    actor_fields = actor.get("fields", {})
    other_fields = other.get("fields", {})
    values.update({
        "actor_age_scaled": (actor["age"] - 21) / 25,
        "other_age_scaled": (other["age"] - 21) / 25,
        "absolute_age_gap_scaled": abs(actor["age"] - other["age"]) / 25,
        "same_zone": float(actor.get("zone") == other.get("zone")),
        "actor_soft_observed_fraction": sum(
            actor_fields.get(field) is not None for field in SOFT
        ) / len(SOFT),
        "other_soft_observed_fraction": sum(
            other_fields.get(field) is not None for field in SOFT
        ) / len(SOFT),
    })
    for gender in ("woman", "man", "non_binary"):
        values[f"actor_gender_{gender}"] = float(actor.get("gender") == gender)
        values[f"other_gender_{gender}"] = float(other.get("gender") == gender)
    return values


def _opportunity_count(actor, members):
    return sum(
        other.get("member_id") != actor.get("member_id")
        and other.get("available")
        and eligibility(actor, other)["status"] != "infeasible"
        for other in members.values()
    )


def _completeness_band(count):
    if count == 0:
        return "0"
    if count <= 2:
        return "1-2"
    if count <= 6:
        return "3-6"
    return "7"


def _opportunity_band(count):
    if count == 0:
        return "0"
    if count <= 4:
        return "1-4"
    return "5+"


def collect_episode(seed, variant):
    simulator = Simulator(generate(seed, 200, "directional_calibration", variant))
    memory = None
    snapshots = {}
    for _ in range(60):
        ask = decide({"phase": "ask", "state": simulator.observe(), "memory": memory}, "adaptive_greedy")
        simulator.resolve_asks(ask["asks"])
        state = simulator.observe()
        members = {member["member_id"]: member for member in state["members"]}
        histories = _feedback_history(state)
        match = decide({"phase": "match", "state": state, "memory": ask["memory"]}, "adaptive_greedy")
        previous = len(state["introductions"])
        simulator.advance(match["pairs"])
        new_introductions = simulator.observe()["introductions"][previous:]
        by_pair = {
            tuple(sorted((intro["user_a"], intro["user_b"]))): intro
            for intro in new_introductions
        }
        for raw_pair in match["pairs"]:
            pair = tuple(sorted(raw_pair))
            introduction = by_pair[pair]
            user_a = introduction["user_a"]
            user_b = introduction["user_b"]
            snapshots[introduction["introduction_id"]] = {
                TARGET_A: {
                    "base": _base_features(members[user_a], members[user_b]),
                    "history": _history_snapshot(histories, user_a),
                    "soft_observed_count": sum(
                        members[user_a].get("fields", {}).get(field) is not None
                        for field in SOFT
                    ),
                    "candidate_opportunity_count": _opportunity_count(members[user_a], members),
                },
                TARGET_B: {
                    "base": _base_features(members[user_b], members[user_a]),
                    "history": _history_snapshot(histories, user_b),
                    "soft_observed_count": sum(
                        members[user_b].get("fields", {}).get(field) is not None
                        for field in SOFT
                    ),
                    "candidate_opportunity_count": _opportunity_count(members[user_b], members),
                },
                "assigned_day": introduction["assigned_day"],
                "response_deadline_day": introduction["response_deadline_day"],
            }
        memory = match["memory"]

    for _ in range(40):
        simulator.advance([])
    final_state = simulator.observe()
    if final_state["day"] < 100:
        raise AssertionError("follow-up did not mature every response window")
    events_by_intro = {}
    for event in final_state["feedback"]:
        events_by_intro.setdefault(event["introduction_id"], []).append(event)

    rows = []
    for introduction in final_state["introductions"]:
        intro_id = introduction["introduction_id"]
        snapshot = snapshots[intro_id]
        if introduction["response_deadline_day"] > final_state["day"]:
            raise AssertionError("right-censored response entered calibration data")
        intro_events = events_by_intro.get(intro_id, [])
        for target, member_id in (
            (TARGET_A, introduction["user_a"]),
            (TARGET_B, introduction["user_b"]),
        ):
            response_events = [
                event for event in intro_events
                if event.get("event") == "introduction_response"
                and event.get("member_id") == member_id
            ]
            if not response_events:
                raise AssertionError("mature introduction is missing its response event")
            label = int(recorded_yes_by_deadline(introduction, intro_events, member_id))
            rows.append({
                "seed": seed,
                "variant": variant,
                "target": target,
                "label": label,
                "base": snapshot[target]["base"],
                "history": snapshot[target]["history"],
                "soft_observed_count": snapshot[target]["soft_observed_count"],
                "candidate_opportunity_count": snapshot[target]["candidate_opportunity_count"],
            })
    return rows


def _collect_job(job):
    seed, variant = job
    return seed, variant, collect_episode(seed, variant)


def collect_rows(seeds, variants, workers):
    jobs = [(seed, variant) for variant in variants for seed in seeds]
    if workers > 1:
        with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as executor:
            completed = list(executor.map(_collect_job, jobs))
    else:
        completed = [_collect_job(job) for job in jobs]
    return [row for _, _, episode_rows in completed for row in episode_rows]


def _posterior(successes, trials, mean):
    return (successes + mean * HISTORY_STRENGTH) / (trials + HISTORY_STRENGTH)


def _prepare(row, response_mean, yes_mean):
    values = dict(row["base"])
    history = row["history"]
    values.update({
        "actor_response_history_logit": _logit(_posterior(
            history["responses"], history["response_trials"], response_mean,
        )),
        "actor_yes_history_logit": _logit(_posterior(
            history["yeses"], history["response_trials"], yes_mean,
        )),
        "actor_history_trials_log": math.log1p(history["response_trials"]),
    })
    return values


def fit_model(training_rows):
    response_mean = sum(
        row["history"]["responses"] for row in training_rows
    ) / max(1, sum(row["history"]["response_trials"] for row in training_rows))
    # Use the actual training target prevalence as the cold-start prior. It is
    # computed from training seeds only.
    yes_mean = statistics.mean(row["label"] for row in training_rows)
    prepared = [
        (_prepare(row, response_mean, yes_mean), row["label"])
        for row in training_rows
    ]
    feature_names = tuple(sorted({name for values, _ in prepared for name in values}))
    specification = _fit_logistic(
        prepared,
        feature_names,
        l2=0.01,
        iterations=320,
        balanced=False,
    )
    return {
        "target": "recorded Yes introduction response by the seven-day response deadline",
        "cold_start_priors": {
            "response_mean": response_mean,
            "yes_by_deadline_mean": yes_mean,
            "strength": HISTORY_STRENGTH,
        },
        "feature_names": feature_names,
        "specification": specification,
    }


def raw_predict(model, row):
    priors = model["cold_start_priors"]
    values = _prepare(row, priors["response_mean"], priors["yes_by_deadline_mean"])
    specification = model["specification"]
    linear = specification["intercept"] + sum(
        coefficient * values.get(name, 0.0)
        for name, coefficient in specification["coefficients"].items()
    )
    return _sigmoid(linear)


def fit_calibrator(model, calibration_rows):
    examples = []
    for row in calibration_rows:
        probability = raw_predict(model, row)
        examples.append(({"raw_logit": _logit(probability)}, row["label"]))
    return _fit_logistic(
        examples,
        ("raw_logit",),
        l2=0.001,
        iterations=500,
        balanced=False,
    )


def predict(model, row):
    probability = raw_predict(model, row)
    calibrator = model.get("calibrator")
    if not calibrator:
        return probability
    linear = (
        calibrator["intercept"]
        + calibrator["coefficients"]["raw_logit"] * _logit(probability)
    )
    return _sigmoid(linear)


def _auc(rows):
    positives = sum(row["label"] for row in rows)
    negatives = len(rows) - positives
    if not positives or not negatives:
        return None
    ordered = sorted(rows, key=lambda row: row["prediction"])
    rank_sum = 0.0
    index = 0
    while index < len(ordered):
        end = index + 1
        while end < len(ordered) and ordered[end]["prediction"] == ordered[index]["prediction"]:
            end += 1
        average_rank = (index + 1 + end) / 2
        rank_sum += average_rank * sum(row["label"] for row in ordered[index:end])
        index = end
    return (rank_sum - positives * (positives + 1) / 2) / (positives * negatives)


def _equal_count_bins(rows, count=10):
    ordered = sorted(rows, key=lambda row: row["prediction"])
    bins = []
    for index in range(min(count, len(ordered))):
        start = index * len(ordered) // min(count, len(ordered))
        end = (index + 1) * len(ordered) // min(count, len(ordered))
        selected = ordered[start:end]
        if selected:
            bins.append({
                "count": len(selected),
                "minimum_prediction": min(row["prediction"] for row in selected),
                "maximum_prediction": max(row["prediction"] for row in selected),
                "mean_prediction": statistics.mean(row["prediction"] for row in selected),
                "observed_rate": statistics.mean(row["label"] for row in selected),
            })
    return bins


def calibration_metrics(rows):
    if not rows:
        raise ValueError("calibration group is empty")
    labels = [row["label"] for row in rows]
    predictions = [row["prediction"] for row in rows]
    bins = []
    for index in range(10):
        lower = index / 10
        upper = (index + 1) / 10
        selected = [
            row for row in rows
            if lower <= row["prediction"] < upper
            or (index == 9 and row["prediction"] == 1.0)
        ]
        if selected:
            bins.append({
                "lower": lower,
                "upper": upper,
                "count": len(selected),
                "mean_prediction": statistics.mean(row["prediction"] for row in selected),
                "observed_rate": statistics.mean(row["label"] for row in selected),
            })
    brier = statistics.mean((prediction - label) ** 2 for prediction, label in zip(predictions, labels))
    log_loss = -statistics.mean(
        label * math.log(min(1 - 1e-12, max(1e-12, prediction)))
        + (1 - label) * math.log(min(1 - 1e-12, max(1e-12, 1 - prediction)))
        for prediction, label in zip(predictions, labels)
    )
    equal_count_bins = _equal_count_bins(rows)
    return {
        "examples": len(rows),
        "positives": sum(labels),
        "observed_rate": statistics.mean(labels),
        "mean_prediction": statistics.mean(predictions),
        "calibration_in_the_large": statistics.mean(predictions) - statistics.mean(labels),
        "brier_score": brier,
        "log_loss": log_loss,
        "auc": _auc(rows),
        "expected_calibration_error": sum(
            item["count"] / len(rows) * abs(item["mean_prediction"] - item["observed_rate"])
            for item in bins
        ),
        "equal_width_bins": bins,
        "equal_count_expected_calibration_error": sum(
            item["count"] / len(rows) * abs(item["mean_prediction"] - item["observed_rate"])
            for item in equal_count_bins
        ),
        "equal_count_bins": equal_count_bins,
    }


def _percentile(values, probability):
    ordered = sorted(values)
    position = probability * (len(ordered) - 1)
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def seed_cluster_intervals(rows, resamples, bootstrap_seed):
    if resamples < 1:
        raise ValueError("resamples must be positive")
    seeds = sorted({row["seed"] for row in rows})
    variants = sorted({row["variant"] for row in rows})
    if not seeds or not variants:
        raise ValueError("calibration rows must not be empty")
    for seed in seeds:
        present = {row["variant"] for row in rows if row["seed"] == seed}
        if present != set(variants):
            raise ValueError("every calibration seed must contain every variant")
    bin_by_row = {}
    for variant in variants:
        variant_rows = sorted(
            (row for row in rows if row["variant"] == variant),
            key=lambda row: row["prediction"],
        )
        bin_count = min(10, len(variant_rows))
        for index, row in enumerate(variant_rows):
            bin_by_row[id(row)] = min(bin_count - 1, index * bin_count // len(variant_rows))

    by_seed = {}
    for seed in seeds:
        by_seed[seed] = {}
        for variant in variants:
            selected = [
                row for row in rows
                if row["seed"] == seed and row["variant"] == variant
            ]
            bins = [
                {"count": 0, "prediction_sum": 0.0, "label_sum": 0.0}
                for _ in range(min(10, sum(row["variant"] == variant for row in rows)))
            ]
            for row in selected:
                item = bins[bin_by_row[id(row)]]
                item["count"] += 1
                item["prediction_sum"] += row["prediction"]
                item["label_sum"] += row["label"]
            by_seed[seed][variant] = {
                "count": len(selected),
                "brier_sum": sum(
                    (row["prediction"] - row["label"]) ** 2 for row in selected
                ),
                "calibration_sum": sum(
                    row["prediction"] - row["label"] for row in selected
                ),
                "bins": bins,
            }
    generator = random.Random(bootstrap_seed)
    samples = {
        "brier_score": [],
        "calibration_in_the_large": [],
        "equal_count_expected_calibration_error": [],
    }
    for _ in range(resamples):
        selected = [generator.choice(seeds) for _ in seeds]
        variant_metrics = {}
        for variant in variants:
            parts = [by_seed[selected_seed][variant] for selected_seed in selected]
            count = sum(part["count"] for part in parts)
            bin_totals = []
            for bin_index in range(len(parts[0]["bins"])):
                bin_totals.append({
                    "count": sum(part["bins"][bin_index]["count"] for part in parts),
                    "prediction_sum": sum(
                        part["bins"][bin_index]["prediction_sum"] for part in parts
                    ),
                    "label_sum": sum(
                        part["bins"][bin_index]["label_sum"] for part in parts
                    ),
                })
            variant_metrics[variant] = {
                "brier_score": sum(part["brier_sum"] for part in parts) / count,
                "calibration_in_the_large": sum(
                    part["calibration_sum"] for part in parts
                ) / count,
                "equal_count_expected_calibration_error": sum(
                    abs(item["prediction_sum"] - item["label_sum"])
                    for item in bin_totals
                ) / count,
            }
        for metric in samples:
            samples[metric].append(statistics.mean(
                variant_metrics[variant][metric] for variant in variants
            ))
    return {
        "method": "percentile bootstrap clustered by seed with equal scenario weighting",
        "seed_groups": len(seeds),
        "variants_per_seed": len(variants),
        "resamples": resamples,
        "bootstrap_seed": bootstrap_seed,
        "ece_bins": "fixed holdout equal-count bins within each scenario variant",
        "intervals": {
            name: {
                "lower": _percentile(values, 0.025),
                "upper": _percentile(values, 0.975),
            }
            for name, values in samples.items()
        },
    }


def paired_brier_difference_intervals(rows, reference_rows, resamples, bootstrap_seed):
    """Compare predictions while keeping each generated seed world together."""
    if resamples < 1:
        raise ValueError("resamples must be positive")
    if len(rows) != len(reference_rows) or not rows:
        raise ValueError("paired prediction sets must have the same nonzero length")
    for observed, reference in zip(rows, reference_rows):
        identity = ("seed", "variant", "target", "label")
        if any(observed[key] != reference[key] for key in identity):
            raise ValueError("paired prediction rows are not aligned")
    seeds = sorted({row["seed"] for row in rows})
    variants = sorted({row["variant"] for row in rows})
    for seed in seeds:
        present = {row["variant"] for row in rows if row["seed"] == seed}
        if present != set(variants):
            raise ValueError("every paired seed must contain every variant")
    paired = [
        dict(
            seed=row["seed"],
            variant=row["variant"],
            difference=(row["prediction"] - row["label"]) ** 2
            - (reference["prediction"] - reference["label"]) ** 2,
        )
        for row, reference in zip(rows, reference_rows)
    ]
    by_seed = {
        seed: {
            variant: {
                "count": sum(
                    row["seed"] == seed and row["variant"] == variant for row in paired
                ),
                "sum": sum(
                    row["difference"] for row in paired
                    if row["seed"] == seed and row["variant"] == variant
                ),
            }
            for variant in variants
        }
        for seed in seeds
    }

    def macro_mean(selected_seeds):
        return statistics.mean(
            sum(by_seed[seed][variant]["sum"] for seed in selected_seeds)
            / sum(by_seed[seed][variant]["count"] for seed in selected_seeds)
            for variant in variants
        )

    generator = random.Random(bootstrap_seed)
    samples = []
    for _ in range(resamples):
        selected = [generator.choice(seeds) for _ in seeds]
        samples.append(macro_mean(selected))
    return {
        "metric": "challenger Brier minus reference Brier",
        "mean_difference": macro_mean(seeds),
        "method": "paired percentile bootstrap clustered by seed with equal scenario weighting",
        "seed_groups": len(seeds),
        "variants_per_seed": len(variants),
        "resamples": resamples,
        "bootstrap_seed": bootstrap_seed,
        "confidence_level": 0.95,
        "lower": _percentile(samples, 0.025),
        "upper": _percentile(samples, 0.975),
    }


def equal_variant_metrics(rows, variants):
    """Average scenario metrics equally instead of weighting by assignments."""
    by_variant = {
        variant: calibration_metrics([row for row in rows if row["variant"] == variant])
        for variant in variants
    }
    metrics = (
        "observed_rate",
        "mean_prediction",
        "calibration_in_the_large",
        "brier_score",
        "log_loss",
        "expected_calibration_error",
        "equal_count_expected_calibration_error",
    )
    return {
        "scenario_weighting": "equal",
        **{
            metric: statistics.mean(by_variant[variant][metric] for variant in variants)
            for metric in metrics
        },
    }


def run_audit(
    training_seeds,
    calibration_seeds,
    holdout_seeds,
    variants,
    workers,
    resamples,
    bootstrap_seed,
):
    if not training_seeds or not calibration_seeds or not holdout_seeds:
        raise ValueError("fit, calibration and holdout must each contain seeds")
    if not variants:
        raise ValueError("at least one scenario variant is required")
    if any(len(values) != len(set(values)) for values in (
        training_seeds, calibration_seeds, holdout_seeds,
    )):
        raise ValueError("seed splits must not contain duplicate seeds")
    split_sets = [set(training_seeds), set(calibration_seeds), set(holdout_seeds)]
    if any(left & right for index, left in enumerate(split_sets) for right in split_sets[index + 1:]):
        raise ValueError("fit, calibration and holdout seeds must be disjoint")
    training_rows = collect_rows(training_seeds, variants, workers)
    calibration_rows = collect_rows(calibration_seeds, variants, workers)
    holdout_rows = collect_rows(holdout_seeds, variants, workers)
    model = fit_model(training_rows)
    model["calibrator"] = fit_calibrator(model, calibration_rows)
    evaluated = [dict(row, prediction=predict(model, row)) for row in holdout_rows]
    raw_evaluated = [dict(row, prediction=raw_predict(model, row)) for row in holdout_rows]
    overall = calibration_metrics(evaluated)
    by_target = {
        target: calibration_metrics([row for row in evaluated if row["target"] == target])
        for target in (TARGET_A, TARGET_B)
    }
    by_variant = {
        variant: calibration_metrics([row for row in evaluated if row["variant"] == variant])
        for variant in variants
    }
    baseline_rows = [
        dict(row, prediction=model["cold_start_priors"]["yes_by_deadline_mean"])
        for row in holdout_rows
    ]
    by_profile_completeness = {
        band: calibration_metrics([
            row for row in evaluated
            if _completeness_band(row["soft_observed_count"]) == band
        ])
        for band in ("0", "1-2", "3-6", "7")
        if any(_completeness_band(row["soft_observed_count"]) == band for row in evaluated)
    }
    by_candidate_opportunity = {
        band: calibration_metrics([
            row for row in evaluated
            if _opportunity_band(row["candidate_opportunity_count"]) == band
        ])
        for band in ("0", "1-4", "5+")
        if any(_opportunity_band(row["candidate_opportunity_count"]) == band for row in evaluated)
    }
    return {
        "design": {
            "targets": {
                TARGET_A: "Probability that the canonical user_a endpoint records Yes by its seven-day deadline.",
                TARGET_B: "Probability that the canonical user_b endpoint records Yes by its seven-day deadline.",
            },
            "orientation_note": "user_a and user_b are canonical pair positions; the same directional estimator is applied after swapping actor and candidate.",
            "missing_response_rule": "No response by the deadline is target 0 because the defined Yes-by-deadline event did not occur; it is not labelled dislike.",
            "maturity": "All assignments receive 40 follow-up days; no right-censored response enters evaluation.",
            "feature_time": "Public observation immediately before assignment; no member ID, latent truth or future feedback is used.",
            "policy_use": "Separate diagnostic only; probabilities do not rank pairs in the selected policy.",
            "policy_mode": "adaptive_greedy",
            "scenario_weighting": "equal in reported macro metrics and seed-clustered intervals",
            "training_seeds": training_seeds,
            "calibration_seeds": calibration_seeds,
            "holdout_seeds": holdout_seeds,
            "variants": variants,
        },
        "sample": {
            "training_directional_examples": len(training_rows),
            "calibration_directional_examples": len(calibration_rows),
            "holdout_directional_examples": len(holdout_rows),
            "training_seed_groups": len(training_seeds),
            "calibration_seed_groups": len(calibration_seeds),
            "holdout_seed_groups": len(holdout_seeds),
            "right_censored_holdout_examples": 0,
        },
        "model": model,
        "holdout": {
            "overall": overall,
            "equal_variant_overall": equal_variant_metrics(evaluated, variants),
            "before_platt_calibration": calibration_metrics(raw_evaluated),
            "before_platt_equal_variant": equal_variant_metrics(raw_evaluated, variants),
            "by_target": by_target,
            "by_variant": by_variant,
            "by_profile_completeness": by_profile_completeness,
            "by_candidate_opportunity": by_candidate_opportunity,
            "seed_cluster_intervals": seed_cluster_intervals(
                evaluated, resamples, bootstrap_seed,
            ),
            "constant_training_prevalence_baseline": calibration_metrics(baseline_rows),
            "constant_baseline_equal_variant": equal_variant_metrics(baseline_rows, variants),
            "paired_brier_vs_constant": paired_brier_difference_intervals(
                evaluated, baseline_rows, resamples, bootstrap_seed + 1,
            ),
            "paired_brier_platt_minus_raw": paired_brier_difference_intervals(
                evaluated, raw_evaluated, resamples, bootstrap_seed + 2,
            ),
            "predictions": [
                {
                    "seed": calibrated["seed"],
                    "variant": calibrated["variant"],
                    "target": calibrated["target"],
                    "label": calibrated["label"],
                    "prediction": calibrated["prediction"],
                    "before_platt_prediction": raw["prediction"],
                    "soft_observed_count": calibrated["soft_observed_count"],
                    "candidate_opportunity_count": calibrated["candidate_opportunity_count"],
                }
                for calibrated, raw in zip(evaluated, raw_evaluated)
            ],
        },
    }


def _parse_seeds(value):
    if "-" in value and "," not in value:
        start, end = (int(part) for part in value.split("-"))
        return list(range(start, end + 1))
    return [int(part) for part in value.split(",")]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--training-seeds", default="6001-6020")
    parser.add_argument("--calibration-seeds", default="6031-6040")
    parser.add_argument("--holdout-seeds", default="6101-6120")
    parser.add_argument("--variants", default="all")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--resamples", type=int, default=5000)
    parser.add_argument("--bootstrap-seed", type=int, default=1701)
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "corrected_directional_calibration.json")
    args = parser.parse_args()
    training_seeds = _parse_seeds(args.training_seeds)
    calibration_seeds = _parse_seeds(args.calibration_seeds)
    holdout_seeds = _parse_seeds(args.holdout_seeds)
    variants = list(VARIANTS) if args.variants == "all" else args.variants.split(",")
    if not variants or any(variant not in VARIANTS for variant in variants):
        parser.error("Choose at least one recognized variant")
    payload = run_audit(
        training_seeds, calibration_seeds, holdout_seeds, variants,
        args.workers, args.resamples, args.bootstrap_seed,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(args.output),
        "sample": payload["sample"],
        "holdout": payload["holdout"],
    }, indent=2))


if __name__ == "__main__":
    main()
