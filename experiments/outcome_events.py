"""Strict event interpretation shared by evidence audits.

The simulator emits one event of each required type and member. Rejecting
duplicates keeps a corrupted or hand-edited evidence file from silently
changing an outcome. Boundary checks use the published inclusive windows.
"""
from __future__ import annotations


_ANY_MEMBER = object()


def _is_day(value):
    return type(value) is int


def _one(events, event_name, member_id=_ANY_MEMBER):
    selected = [
        event for event in events
        if event.get("event") == event_name
        and (member_id is _ANY_MEMBER or event.get("member_id") == member_id)
    ]
    if len(selected) > 1:
        label = event_name if member_id is None else f"{event_name}/{member_id}"
        raise ValueError(f"duplicate outcome event: {label}")
    return selected[0] if selected else None


def _validate_introduction(introduction):
    assigned = introduction.get("assigned_day")
    deadline = introduction.get("response_deadline_day")
    if not _is_day(assigned) or not _is_day(deadline) or deadline < assigned:
        raise ValueError("invalid introduction response window")
    endpoints = (introduction.get("user_a"), introduction.get("user_b"))
    if not all(isinstance(member_id, str) for member_id in endpoints) or endpoints[0] == endpoints[1]:
        raise ValueError("invalid introduction endpoints")
    return assigned, deadline, endpoints


def _validate_event_actors(introduction, events):
    _, _, endpoints = _validate_introduction(introduction)
    for event in events:
        name = event.get("event")
        member_id = event.get("member_id")
        if name in ("introduction_response", "second_meeting_intention") and member_id not in endpoints:
            raise ValueError(f"invalid event member for {name}")
        if name == "date_happened" and member_id is not None:
            raise ValueError("date_happened must be pair-level")


def recorded_yes_by_deadline(introduction, events, member_id):
    """Return whether one endpoint recorded Yes inside its response window."""
    assigned, deadline, endpoints = _validate_introduction(introduction)
    if member_id not in endpoints:
        raise ValueError("response member is not an introduction endpoint")
    _validate_event_actors(introduction, events)
    event = _one(events, "introduction_response", member_id)
    if event is None or event.get("value") != "yes":
        return False
    occurred = event.get("occurred_day")
    observed = event.get("observed_day")
    return (
        _is_day(occurred)
        and _is_day(observed)
        and assigned <= occurred <= deadline
        and occurred <= observed <= deadline
    )


def classify_funnel(introduction, events):
    """Classify mutual response, date and MSMI without collapsing stages."""
    assigned, _, endpoints = _validate_introduction(introduction)
    _validate_event_actors(introduction, events)
    mutual = all(
        recorded_yes_by_deadline(introduction, events, member_id)
        for member_id in endpoints
    )
    date = _one(events, "date_happened", None)
    date_day = date.get("occurred_day") if date and date.get("value") is True else None
    response_days = [
        _one(events, "introduction_response", member_id).get("occurred_day")
        for member_id in endpoints
    ] if mutual else []
    dated = (
        mutual
        and _is_day(date_day)
        and assigned <= date_day <= assigned + 30
        and date_day >= max(response_days)
        and _is_day(date.get("observed_day"))
        and date_day <= date["observed_day"]
    )
    second_yes = False
    if dated:
        second_yes = all(
            _second_yes_in_window(events, member_id, date_day)
            for member_id in endpoints
        )
    return {"mutual_acceptance": mutual, "date_happened": dated, "msmi": dated and second_yes}


def _second_yes_in_window(events, member_id, date_day):
    event = _one(events, "second_meeting_intention", member_id)
    if event is None or event.get("value") != "yes":
        return False
    occurred = event.get("occurred_day")
    observed = event.get("observed_day")
    return (
        _is_day(occurred)
        and _is_day(observed)
        and date_day <= occurred <= date_day + 3
        and occurred <= observed <= date_day + 3
    )
