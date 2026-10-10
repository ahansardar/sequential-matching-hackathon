"""Verify release checksums, schema semantics and referential integrity."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from experiments.outcome_events import validate_event_sequence
from kit import GENDERS, HARD, SOFT


ROOT = Path(__file__).resolve().parent
VERSION = "1.0.0"
FORBIDDEN = {
    "truth", "bias", "second_bias", "response_rate", "exit_day",
    "email", "phone", "full_name", "password",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_lines(path):
    rows = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as error:
            raise ValueError(f"{path}:{line_number}: invalid JSON: {error}") from error
    return rows


def validate_member(member, pool_id, snapshot_day):
    member_id = member.get("member_id")
    require(isinstance(member_id, str), f"{pool_id}: member ID must be a string")
    require(member.get("synthetic") is True, f"{pool_id}/{member_id}: non-synthetic member")
    require(member.get("pool_id") == pool_id, f"{pool_id}/{member_id}: wrong pool")
    require(not FORBIDDEN.intersection(member), f"{pool_id}/{member_id}: private or hidden field")
    require(type(member.get("age")) is int and member["age"] >= 18, f"{pool_id}/{member_id}: invalid age")
    require(member.get("gender") in GENDERS, f"{pool_id}/{member_id}: invalid gender")
    arrived = member.get("arrived_day")
    require(type(arrived) is int and 0 <= arrived <= snapshot_day, f"{pool_id}/{member_id}: invalid arrival")
    fields = member.get("fields")
    statuses = member.get("field_status")
    observed_days = member.get("field_observed_day")
    expected = set(HARD + SOFT)
    require(isinstance(fields, dict) and set(fields) == expected, f"{pool_id}/{member_id}: field keys")
    require(isinstance(statuses, dict) and set(statuses) == expected, f"{pool_id}/{member_id}: status keys")
    require(isinstance(observed_days, dict) and set(observed_days) == expected, f"{pool_id}/{member_id}: observed-day keys")
    for field in HARD + SOFT:
        value = fields[field]
        status = statuses[field]
        observed_day = observed_days[field]
        require(status in {"observed", "not_asked", "declined"}, f"{pool_id}/{member_id}/{field}: status")
        if status == "observed":
            require(value is not None, f"{pool_id}/{member_id}/{field}: observed null")
            require(type(observed_day) is int and arrived <= observed_day <= snapshot_day,
                    f"{pool_id}/{member_id}/{field}: invalid observed day")
        else:
            require(value is None and observed_day is None,
                    f"{pool_id}/{member_id}/{field}: unknown field exposes a value")


def validate_pool(pool_id, manifest_row):
    folder = ROOT / "data" / pool_id
    state = json.loads((folder / "state.json").read_text(encoding="utf-8"))
    snapshot_day = manifest_row["snapshot_day"]
    require(state.get("synthetic") is True and state.get("schema_version") == VERSION,
            f"{pool_id}: invalid state header")
    require(state.get("day") == snapshot_day, f"{pool_id}: snapshot day mismatch")

    members = read_lines(folder / "members.jsonl")
    member_ids = [member.get("member_id") for member in members]
    require(len(member_ids) == len(set(member_ids)), f"{pool_id}: duplicate member ID")
    for member in members:
        validate_member(member, pool_id, snapshot_day)
    by_member = {member["member_id"]: member for member in members}

    introductions = read_lines(folder / "introductions.jsonl")
    introduction_ids = [row.get("introduction_id") for row in introductions]
    require(all(isinstance(value, str) for value in introduction_ids), f"{pool_id}: invalid introduction ID")
    require(len(introduction_ids) == len(set(introduction_ids)), f"{pool_id}: duplicate introduction ID")
    seen_pairs = set()
    for introduction in introductions:
        endpoints = (introduction.get("user_a"), introduction.get("user_b"))
        require(endpoints[0] in by_member and endpoints[1] in by_member and endpoints[0] != endpoints[1],
                f"{pool_id}/{introduction.get('introduction_id')}: invalid endpoints")
        pair = tuple(sorted(endpoints))
        require(pair not in seen_pairs, f"{pool_id}: repeated historical pair")
        seen_pairs.add(pair)
        assigned = introduction.get("assigned_day")
        deadline = introduction.get("response_deadline_day")
        require(type(assigned) is int and 0 <= assigned < snapshot_day,
                f"{pool_id}/{introduction['introduction_id']}: invalid assignment day")
        require(type(deadline) is int and deadline == assigned + 7,
                f"{pool_id}/{introduction['introduction_id']}: invalid deadline")
        require(max(by_member[member_id]["arrived_day"] for member_id in endpoints) <= assigned,
                f"{pool_id}/{introduction['introduction_id']}: assigned before arrival")

    by_introduction = {row["introduction_id"]: row for row in introductions}
    feedback = read_lines(folder / "feedback.jsonl")
    events_by_introduction = {introduction_id: [] for introduction_id in introduction_ids}
    for event in feedback:
        introduction_id = event.get("introduction_id")
        require(introduction_id in by_introduction, f"{pool_id}: orphan feedback")
        observed = event.get("observed_day")
        require(type(observed) is int and observed <= snapshot_day,
                f"{pool_id}/{introduction_id}: feedback after snapshot")
        events_by_introduction[introduction_id].append(event)
    for introduction_id, events in events_by_introduction.items():
        validate_event_sequence(by_introduction[introduction_id], events)

    conversations = read_lines(folder / "conversations.jsonl")
    conversation_ids = [row.get("member_id") for row in conversations]
    require(len(conversation_ids) == len(set(conversation_ids)), f"{pool_id}: duplicate conversation member")
    for conversation in conversations:
        member_id = conversation.get("member_id")
        require(member_id in by_member, f"{pool_id}: orphan conversation")
        require(conversation.get("synthetic") is True, f"{pool_id}/{member_id}: non-synthetic conversation")
        require(type(conversation.get("observed_day")) is int
                and by_member[member_id]["arrived_day"] <= conversation["observed_day"] <= snapshot_day,
                f"{pool_id}/{member_id}: invalid conversation day")

    require(state.get("members") == members, f"{pool_id}: state/member table mismatch")
    require(state.get("introductions") == introductions, f"{pool_id}: state/introduction table mismatch")
    require(state.get("feedback") == feedback, f"{pool_id}: state/feedback table mismatch")
    require(len(members) == manifest_row["members"], f"{pool_id}: member manifest count")
    require(len(introductions) == manifest_row["introductions"], f"{pool_id}: introduction manifest count")
    require(len(feedback) == manifest_row["feedback_events"], f"{pool_id}: feedback manifest count")
    return {
        "members": len(members),
        "introductions": len(introductions),
        "feedback": len(feedback),
        "conversations": len(conversations),
    }


def verify():
    checksums = json.loads((ROOT / "data_checksums.json").read_text(encoding="utf-8"))
    for name, expected in checksums.items():
        actual = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
        require(actual == expected, f"checksum mismatch: {name}")

    manifest = json.loads((ROOT / "data_manifest.json").read_text(encoding="utf-8"))
    require(manifest.get("schema_version") == VERSION and manifest.get("synthetic") is True,
            "invalid manifest header")
    split_pools = [pool for split in manifest["splits"].values() for pool in split]
    require(len(split_pools) == len(set(split_pools)), "manifest splits overlap")
    rows = {row["pool_id"]: row for row in manifest["pools"]}
    require(set(split_pools) == set(rows), "manifest pools and splits disagree")

    counts = {"members": 0, "introductions": 0, "feedback": 0, "conversations": 0}
    for pool_id in split_pools:
        pool_counts = validate_pool(pool_id, rows[pool_id])
        for key, value in pool_counts.items():
            counts[key] += value
    require(counts == {"members": 2000, "introductions": 613, "feedback": 1270, "conversations": 1129},
            f"release counts changed: {counts}")
    result = {
        "verified": True,
        "schema_semantics": True,
        "referential_integrity": True,
        "temporal_integrity": True,
        "counts": counts,
        "files": len(checksums),
    }
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    verify()
