"""Observable feature extraction for the offline outcome-model experiment."""
from __future__ import annotations

import functools
import json
import math
from pathlib import Path

from kit import SOFT


MODEL_PATH = Path(__file__).with_name("outcome_model.json")
PAIR_FEATURES = tuple(
    name
    for field in SOFT
    for name in (f"{field}_match", f"{field}_mismatch")
)


def _clip(value, lower=1e-6, upper=1 - 1e-6):
    return min(upper, max(lower, value))


def _logit(value):
    value = _clip(value)
    return math.log(value / (1 - value))


def _sigmoid(value):
    if value >= 0:
        return 1 / (1 + math.exp(-value))
    exponential = math.exp(value)
    return exponential / (1 + exponential)


@functools.lru_cache(maxsize=1)
def load_model(path=None):
    model_path = Path(path) if path else MODEL_PATH
    return json.loads(model_path.read_text(encoding="utf-8"))


def feedback_history(state):
    """Return mature per-member counts available in the current observation."""
    histories = {}

    def member_history(member_id):
        return histories.setdefault(member_id, {
            "response_trials": 0,
            "responses": 0,
            "accept_trials": 0,
            "accepts": 0,
            "second_trials": 0,
            "second_successes": 0,
        })

    date_days = {
        event["introduction_id"]: event.get("occurred_day")
        for event in state.get("feedback", [])
        if event.get("event") == "date_happened" and event.get("value") is True
    }
    for event in state.get("feedback", []):
        member_id = event.get("member_id")
        if not member_id:
            continue
        history = member_history(member_id)
        if event.get("event") == "introduction_response":
            history["response_trials"] += 1
            if event.get("value") is not None:
                history["responses"] += 1
                history["accept_trials"] += 1
                if event.get("value") == "yes":
                    history["accepts"] += 1
        elif (
            event.get("event") == "second_meeting_intention"
            and event.get("introduction_id") in date_days
        ):
            history["second_trials"] += 1
            date_day = date_days[event["introduction_id"]]
            if (
                event.get("value") == "yes"
                and event.get("occurred_day") is not None
                and event["occurred_day"] - date_day <= 3
            ):
                history["second_successes"] += 1
    return histories


def pair_comparisons(left, right):
    comparisons = {}
    left_fields = left.get("fields", {})
    right_fields = right.get("fields", {})
    for field in SOFT:
        left_value = left_fields.get(field)
        right_value = right_fields.get(field)
        comparisons[field] = (
            None
            if left_value is None or right_value is None
            else left_value == right_value
        )
    return comparisons


def comparison_features(comparisons):
    values = {}
    for field in SOFT:
        comparison = comparisons.get(field)
        values[f"{field}_match"] = float(comparison is True)
        values[f"{field}_mismatch"] = float(comparison is False)
    return values


def _posterior(successes, trials, mean, strength):
    return (successes + mean * strength) / (trials + strength)


def history_rates(history, model):
    priors = model["priors"]
    history = history or {}
    return {
        "response": _posterior(
            history.get("responses", 0),
            history.get("response_trials", 0),
            priors["response_mean"],
            priors["response_strength"],
        ),
        "accept": _posterior(
            history.get("accepts", 0),
            history.get("accept_trials", 0),
            priors["accept_mean"],
            priors["accept_strength"],
        ),
        "second": _posterior(
            history.get("second_successes", 0),
            history.get("second_trials", 0),
            priors["second_mean"],
            priors["second_strength"],
        ),
    }


def _predict(specification, values):
    linear = specification["intercept"]
    for name, coefficient in specification["coefficients"].items():
        linear += coefficient * values.get(name, 0.0)
    return _sigmoid(linear)


def _pair_history_features(left_rates, right_rates):
    return {
        "response_logit_sum": _logit(left_rates["response"]) + _logit(right_rates["response"]),
        "accept_logit_sum": _logit(left_rates["accept"]) + _logit(right_rates["accept"]),
        "second_logit_sum": _logit(left_rates["second"]) + _logit(right_rates["second"]),
    }


def score_pair(
    state,
    left,
    right,
    mode="learned_funnel",
    model=None,
    histories=None,
    rates_by_member=None,
):
    """Estimate pair MSMI probability from information observable now."""
    model = model or load_model()
    comparisons = pair_comparisons(left, right)
    values = comparison_features(comparisons)
    if rates_by_member is None:
        histories = histories if histories is not None else feedback_history(state)
        left_rates = history_rates(histories.get(left["member_id"]), model)
        right_rates = history_rates(histories.get(right["member_id"]), model)
    else:
        left_rates = rates_by_member[left["member_id"]]
        right_rates = rates_by_member[right["member_id"]]

    if mode in {"learned_static", "learned_history"}:
        if mode == "learned_history":
            values.update(_pair_history_features(left_rates, right_rates))
        return _predict(model["models"][mode], values)

    acceptance_specification = model["models"]["acceptance"]
    second_specification = model["models"]["second"]
    left_accept_values = dict(values, accept_history_logit=_logit(left_rates["accept"]))
    right_accept_values = dict(values, accept_history_logit=_logit(right_rates["accept"]))
    left_second_values = dict(values, second_history_logit=_logit(left_rates["second"]))
    right_second_values = dict(values, second_history_logit=_logit(right_rates["second"]))

    return (
        left_rates["response"]
        * right_rates["response"]
        * _predict(acceptance_specification, left_accept_values)
        * _predict(acceptance_specification, right_accept_values)
        * model["date_within_30_probability"]
        * _predict(second_specification, left_second_values)
        * _predict(second_specification, right_second_values)
    )
