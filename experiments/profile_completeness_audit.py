"""Audit service and outcomes by soft-profile completeness.

The controlled condition hides a deterministic share of already observed soft
fields from the policy. The simulator, people, hard constraints and latent
outcomes remain unchanged. Cohorts always use the unmasked information count
recorded when each member first becomes observable.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import copy
import hashlib
import json
from pathlib import Path
import statistics
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluate import VARIANTS, summarise  # noqa: E402
from experiments.confidence_audit import paired_analysis  # noqa: E402
from kit import SOFT, Simulator, eligibility, generate  # noqa: E402
from policy import decide  # noqa: E402
from experiments.outcome_events import classify_funnel  # noqa: E402


BAND_ORDER = ("0", "1-2", "3-6", "7")
OPPORTUNITY_ORDER = ("0", "1-4", "5-14", "15+")


def completeness_band(count):
    if count == 0:
        return "0"
    if count <= 2:
        return "1-2"
    if count <= 6:
        return "3-6"
    return "7"


def opportunity_band(count):
    if count == 0:
        return "0"
    if count <= 4:
        return "1-4"
    if count <= 14:
        return "5-14"
    return "15+"


def arrival_band(day):
    if day == 0:
        return "0"
    if day <= 10:
        return "1-10"
    return "11-20"


def _initial_opportunity(member, members):
    statuses = [
        eligibility(member, other)["status"]
        for other in members
        if other.get("available") and other.get("member_id") != member.get("member_id")
    ]
    return {
        "not_ruled_out": sum(status != "infeasible" for status in statuses),
        "decidable_feasible": sum(status == "feasible" for status in statuses),
    }


def _percentile(values, probability):
    if not values:
        return None
    ordered = sorted(values)
    position = probability * (len(ordered) - 1)
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def _is_masked(seed, member_id, field, rate):
    if rate <= 0:
        return False
    token = f"profile-mask-v1|{seed}|{member_id}|{field}".encode()
    draw = int.from_bytes(hashlib.sha256(token).digest()[:8], "big") / 2**64
    return draw < rate


def mask_soft_information(state, seed, rate):
    masked = copy.deepcopy(state)
    for member in masked.get("members", []):
        for field in SOFT:
            if (
                member.get("fields", {}).get(field) is not None
                and _is_masked(seed, member["member_id"], field, rate)
            ):
                member["fields"][field] = None
                member["field_status"][field] = "not_asked"
                member["field_observed_day"][field] = None
    return masked


def _outcome_sets(state):
    events = state["feedback"]
    by_intro = {}
    for event in events:
        by_intro.setdefault(event["introduction_id"], []).append(event)
    mutual = set()
    dates = set()
    msmi = set()
    for introduction in state["introductions"]:
        intro_id = introduction["introduction_id"]
        intro_events = by_intro.get(intro_id, [])
        outcome = classify_funnel(introduction, intro_events)
        if outcome["mutual_acceptance"]:
            mutual.add(intro_id)
        if outcome["date_happened"]:
            dates.add(intro_id)
        if outcome["msmi"]:
            msmi.add(intro_id)
    return mutual, dates, msmi


def profile_episode(seed, variant, mask_rate):
    simulator = Simulator(generate(seed, 200, "profile_completeness", variant))
    memory = None
    initial_counts = {}
    initial_opportunities = {}
    for _ in range(60):
        raw_ask_state = simulator.observe()
        for member in raw_ask_state["members"]:
            if member["member_id"] not in initial_counts:
                initial_counts[member["member_id"]] = sum(
                    member.get("fields", {}).get(field) is not None for field in SOFT
                )
                initial_opportunities[member["member_id"]] = _initial_opportunity(
                    member, raw_ask_state["members"]
                )
        ask_state = mask_soft_information(raw_ask_state, seed, mask_rate)
        ask = decide({"phase": "ask", "state": ask_state, "memory": memory}, "adaptive_greedy")
        simulator.resolve_asks(ask["asks"])
        match_state = mask_soft_information(simulator.observe(), seed, mask_rate)
        match = decide({"phase": "match", "state": match_state, "memory": ask["memory"]}, "adaptive_greedy")
        simulator.advance(match["pairs"])
        memory = match["memory"]

    decision_end_state = simulator.observe()
    for _ in range(40):
        simulator.advance([])

    final_state = simulator.observe()
    mutual_ids, date_ids, msmi_ids = _outcome_sets(final_state)
    arrived = {
        member_id: member["arrived_day"]
        for member in decision_end_state["members"]
        for member_id in [member["member_id"]]
        if member["arrived_day"] <= 59
    }
    introductions_by_member = {member_id: [] for member_id in arrived}
    for introduction in final_state["introductions"]:
        for member_id in (introduction["user_a"], introduction["user_b"]):
            introductions_by_member[member_id].append(introduction)

    group_rows = {}
    for band in BAND_ORDER:
        member_ids = [
            member_id for member_id in arrived
            if completeness_band(initial_counts[member_id]) == band
        ]
        served = [member_id for member_id in member_ids if introductions_by_member[member_id]]
        waits = [
            min(item["assigned_day"] for item in introductions_by_member[member_id])
            - arrived[member_id]
            for member_id in served
        ]
        mutual_members = {
            member_id for member_id in member_ids
            if any(item["introduction_id"] in mutual_ids for item in introductions_by_member[member_id])
        }
        date_members = {
            member_id for member_id in member_ids
            if any(item["introduction_id"] in date_ids for item in introductions_by_member[member_id])
        }
        msmi_members = {
            member_id for member_id in member_ids
            if any(item["introduction_id"] in msmi_ids for item in introductions_by_member[member_id])
        }
        size = len(member_ids)
        potential_ids = [
            member_id for member_id in member_ids
            if initial_opportunities[member_id]["not_ruled_out"] > 0
        ]
        served_with_potential = sum(member_id in served for member_id in potential_ids)
        group_rows[band] = {
            "members": size,
            "served_members": len(served),
            "coverage": len(served) / max(1, size),
            "unserved_members": size - len(served),
            "unserved_rate": (size - len(served)) / max(1, size),
            "mutual_acceptance_members": len(mutual_members),
            "mutual_acceptance_member_rate": len(mutual_members) / max(1, size),
            "date_members": len(date_members),
            "date_member_rate": len(date_members) / max(1, size),
            "msmi_members": len(msmi_members),
            "msmi_member_rate": len(msmi_members) / max(1, size),
            "assignments": sum(len(introductions_by_member[member_id]) for member_id in member_ids),
            "mean_assignments_per_member": sum(
                len(introductions_by_member[member_id]) for member_id in member_ids
            ) / max(1, size),
            "median_wait_days_served": statistics.median(waits) if waits else None,
            "p90_wait_days_served": _percentile(waits, 0.90),
            "wait_days_served": waits,
            "members_with_potential_partner": len(potential_ids),
            "served_members_with_potential_partner": served_with_potential,
            "coverage_given_potential_partner": (
                served_with_potential / len(potential_ids) if potential_ids else None
            ),
            "mean_initial_not_ruled_out_partners": statistics.mean(
                initial_opportunities[member_id]["not_ruled_out"] for member_id in member_ids
            ) if member_ids else None,
            "mean_initial_decidable_feasible_partners": statistics.mean(
                initial_opportunities[member_id]["decidable_feasible"] for member_id in member_ids
            ) if member_ids else None,
        }

    service_cells = []
    for band in BAND_ORDER:
        for opportunity in OPPORTUNITY_ORDER:
            for arrival in ("0", "1-10", "11-20"):
                member_ids = [
                    member_id for member_id in arrived
                    if completeness_band(initial_counts[member_id]) == band
                    and opportunity_band(initial_opportunities[member_id]["not_ruled_out"]) == opportunity
                    and arrival_band(arrived[member_id]) == arrival
                ]
                if member_ids:
                    served_count = sum(bool(introductions_by_member[member_id]) for member_id in member_ids)
                    service_cells.append({
                        "profile_band": band,
                        "opportunity_band": opportunity,
                        "arrival_band": arrival,
                        "members": len(member_ids),
                        "served_members": served_count,
                        "coverage": served_count / len(member_ids),
                    })

    result = simulator.metrics()
    first = {
        member_id: min(item["assigned_day"] for item in introductions)
        for member_id, introductions in introductions_by_member.items()
        if introductions
    }
    denominator = len(arrived)
    result.update({
        "valid": True,
        "seed": seed,
        "variant": variant,
        "mask_rate": mask_rate,
        "arrived_members": denominator,
        "served_members": len(first),
        "unserved_members": denominator - len(first),
        "coverage": len(first) / max(1, denominator),
        "mutual_acceptances_per_100": 100 * result["mutual_acceptances"] / max(1, denominator),
        "msmi_per_100_arrived_members": 100 * result["mutual_second_meeting_intention"] / max(1, denominator),
        "inference_seconds": 0.0,
        "groups": group_rows,
        "service_cells": service_cells,
    })
    nonempty = [group for group in group_rows.values() if group["members"]]
    result["coverage_gap_max_minus_min"] = max(group["coverage"] for group in nonempty) - min(
        group["coverage"] for group in nonempty
    )
    result["unserved_rate_gap_max_minus_min"] = max(
        group["unserved_rate"] for group in nonempty
    ) - min(group["unserved_rate"] for group in nonempty)
    result["msmi_member_rate_gap_max_minus_min"] = max(
        group["msmi_member_rate"] for group in nonempty
    ) - min(group["msmi_member_rate"] for group in nonempty)
    conditional = [
        group["coverage_given_potential_partner"] for group in nonempty
        if group["coverage_given_potential_partner"] is not None
    ]
    result["coverage_given_potential_partner_gap_max_minus_min"] = (
        max(conditional) - min(conditional) if conditional else 0.0
    )
    return result


def _run_job(job):
    return profile_episode(*job)


def aggregate_groups(rows):
    output = {}
    for band in BAND_ORDER:
        groups = [row["groups"][band] for row in rows]
        members = sum(group["members"] for group in groups)
        served = sum(group["served_members"] for group in groups)
        potential = sum(group["members_with_potential_partner"] for group in groups)
        potential_served = sum(group["served_members_with_potential_partner"] for group in groups)
        waits = [value for group in groups for value in group["wait_days_served"]]
        output[band] = {
            "members": members,
            "served_members": served,
            "coverage": served / max(1, members),
            "unserved_members": members - served,
            "unserved_rate": (members - served) / max(1, members),
            "mutual_acceptance_member_rate": sum(
                group["mutual_acceptance_members"] for group in groups
            ) / max(1, members),
            "date_member_rate": sum(group["date_members"] for group in groups) / max(1, members),
            "msmi_member_rate": sum(group["msmi_members"] for group in groups) / max(1, members),
            "mean_assignments_per_member": sum(group["assignments"] for group in groups) / max(1, members),
            "median_wait_days_served": statistics.median(waits) if waits else None,
            "p90_wait_days_served": _percentile(waits, 0.90),
            "members_with_potential_partner": potential,
            "coverage_given_potential_partner": (
                potential_served / potential if potential else None
            ),
            "mean_initial_not_ruled_out_partners": sum(
                (group["mean_initial_not_ruled_out_partners"] or 0) * group["members"]
                for group in groups
            ) / max(1, members),
            "mean_initial_decidable_feasible_partners": sum(
                (group["mean_initial_decidable_feasible_partners"] or 0) * group["members"]
                for group in groups
            ) / max(1, members),
        }
    return output


def aggregate_service_cells(rows):
    keyed = {}
    for row in rows:
        for cell in row["service_cells"]:
            key = (cell["profile_band"], cell["opportunity_band"], cell["arrival_band"])
            target = keyed.setdefault(key, {"members": 0, "served_members": 0})
            target["members"] += cell["members"]
            target["served_members"] += cell["served_members"]
    return [
        {
            "profile_band": key[0],
            "opportunity_band": key[1],
            "arrival_band": key[2],
            **counts,
            "coverage": counts["served_members"] / counts["members"],
        }
        for key, counts in sorted(keyed.items())
    ]


def run_audit(
    seeds,
    variants,
    mask_rate,
    workers,
    resamples,
    bootstrap_seed,
    unmasked_rows=None,
):
    conditions = {"unmasked": 0.0, "masked": mask_rate}
    rows = {}
    for name, rate in conditions.items():
        if name == "unmasked" and unmasked_rows is not None:
            rows[name] = unmasked_rows
            continue
        jobs = [(seed, variant, rate) for variant in variants for seed in seeds]
        if workers > 1:
            with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as executor:
                rows[name] = list(executor.map(_run_job, jobs))
        else:
            rows[name] = [_run_job(job) for job in jobs]
    paired = {}
    for metric in (
        "msmi_per_100_arrived_members",
        "coverage",
        "unserved_members",
        "coverage_gap_max_minus_min",
        "unserved_rate_gap_max_minus_min",
        "msmi_member_rate_gap_max_minus_min",
        "coverage_given_potential_partner_gap_max_minus_min",
    ):
        paired[metric] = paired_analysis(
            rows["unmasked"], rows["masked"],
            resamples=resamples, seed=bootstrap_seed, metric=metric,
        )
    return {
        "design": {
            "cohort_measure": "unmasked observed soft-field count when member first appears",
            "bands": list(BAND_ORDER),
            "controlled_condition": f"deterministically mask {mask_rate:.0%} of observed soft fields",
            "unchanged": ["generated worlds", "hard constraints", "policy code", "outcome process"],
            "policy_mode": "adaptive_greedy",
            "opportunity_measure": "available arrived partners not ruled out by observed reciprocal hard constraints when the member first appears",
            "opportunity_limit": "not-ruled-out is an opportunity proxy, not proof that missing hard constraints will resolve as feasible",
            "service_strata": ["initial soft-profile band", "arrival band", "initial opportunity band"],
            "paired_by": ["seed", "variant"],
            "bootstrap_cluster": "seed with every variant kept together",
            "seeds": seeds,
            "variants": variants,
        },
        "conditions": {
            name: {
                "summary": summarise(condition_rows),
                "groups": aggregate_groups(condition_rows),
                "opportunity_adjusted_service_cells": aggregate_service_cells(condition_rows),
                "episodes": condition_rows,
            }
            for name, condition_rows in rows.items()
        },
        "paired_masked_minus_unmasked": paired,
    }


def _parse_seeds(value):
    if "-" in value and "," not in value:
        start, end = (int(part) for part in value.split("-"))
        return list(range(start, end + 1))
    return [int(part) for part in value.split(",")]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", default="6201-6220")
    parser.add_argument("--variants", default="all")
    parser.add_argument("--mask-rate", type=float, default=0.5)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--resamples", type=int, default=20000)
    parser.add_argument("--bootstrap-seed", type=int, default=1701)
    parser.add_argument(
        "--input-unmasked",
        type=Path,
        help="Reuse unmasked episode rows from an earlier compatible audit.",
    )
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "corrected_profile_completeness.json")
    args = parser.parse_args()
    if not 0 <= args.mask_rate <= 1:
        parser.error("mask rate must be between zero and one")
    seeds = _parse_seeds(args.seeds)
    variants = list(VARIANTS) if args.variants == "all" else args.variants.split(",")
    unmasked_rows = None
    if args.input_unmasked:
        prior = json.loads(args.input_unmasked.read_text(encoding="utf-8"))
        unmasked_rows = prior["conditions"]["unmasked"]["episodes"]
        expected = {(seed, variant) for seed in seeds for variant in variants}
        present = {(row["seed"], row["variant"]) for row in unmasked_rows}
        if present != expected or len(unmasked_rows) != len(expected):
            parser.error("input unmasked rows do not match requested seeds and variants")
    payload = run_audit(
        seeds, variants, args.mask_rate, args.workers,
        args.resamples, args.bootstrap_seed, unmasked_rows=unmasked_rows,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(args.output),
        "unmasked": payload["conditions"]["unmasked"]["summary"],
        "masked": payload["conditions"]["masked"]["summary"],
        "unmasked_groups": payload["conditions"]["unmasked"]["groups"],
        "paired": payload["paired_masked_minus_unmasked"],
    }, indent=2))


if __name__ == "__main__":
    main()
