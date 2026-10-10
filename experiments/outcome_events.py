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
    if not _is_day(assigned) or not _is_day(deadline) or deadline != assigned + 7:
        raise ValueError("invalid introduction response window")
    endpoints = (introduction.get("user_a"), introduction.get("user_b"))
    if not all(isinstance(member_id, str) for member_id in endpoints) or endpoints[0] == endpoints[1]:
        raise ValueError("invalid introduction endpoints")
    return assigned, deadline, endpoints


def _validate_event_actors(introduction, events):
    _, _, endpoints = _validate_introduction(introduction)
    for event in events:
        introduction_id = event.get("introduction_id")
        if introduction_id is not None and introduction_id != introduction.get("introduction_id"):
            raise ValueError("event belongs to a different introduction")
        name = event.get("event")
        member_id = event.get("member_id")
        if name in ("introduction_response", "second_meeting_intention") and member_id not in endpoints:
            raise ValueError(f"invalid event member for {name}")
        if name == "date_happened" and member_id is not None:
            raise ValueError("date_happened must be pair-level")


def validate_event_sequence(introduction, events):
    """Reject impossible or internally inconsistent mature event sequences."""
    assigned, deadline, endpoints = _validate_introduction(introduction)
    _validate_event_actors(introduction, events)
    allowed = {
        "introduction_response",
        "date_happened",
        "second_meeting_intention",
        "pause_after_mutual_interest",
    }
    seen = set()
    for event in events:
        name = event.get("event")
        if name not in allowed:
            continue
        member_id = event.get("member_id")
        key = (name, member_id)
        if key in seen:
            raise ValueError(f"duplicate outcome event: {name}/{member_id}")
        seen.add(key)
        occurred = event.get("occurred_day")
        observed = event.get("observed_day")
        if not _is_day(observed):
            raise ValueError(f"invalid observed day for {name}")
        if occurred is not None and (not _is_day(occurred) or occurred > observed):
            raise ValueError(f"invalid occurred day for {name}")

        if name == "introduction_response":
            if not assigned <= observed <= deadline:
                raise ValueError("response observed outside deadline window")
            if event.get("value") in ("yes", "no"):
                if occurred is None or not assigned <= occurred <= deadline:
                    raise ValueError("recorded response lacks an in-window occurrence")
            elif event.get("value") is None:
                if occurred is not None or observed != deadline:
                    raise ValueError("missing response must close at the deadline")
            else:
                raise ValueError("invalid introduction response value")
        elif name == "date_happened":
            if event.get("value") not in (True, False) or occurred is None:
                raise ValueError("invalid date event")
        elif name == "second_meeting_intention":
            if event.get("value") in ("yes", "no") and occurred is None:
                raise ValueError("recorded second intention lacks an occurrence day")
            if event.get("value") is None and occurred is not None:
                raise ValueError("missing second intention has an occurrence day")
            if event.get("value") not in ("yes", "no", None):
                raise ValueError("invalid second intention value")
        elif member_id is not None or event.get("value") is not True or occurred is None:
            raise ValueError("invalid pause event")

    responses = {
        member_id: _one(events, "introduction_response", member_id)
        for member_id in endpoints
    }
    mutual_yes = all(
        event is not None and event.get("value") == "yes"
        for event in responses.values()
    )
    date = _one(events, "date_happened", None)
    second_events = [
        _one(events, "second_meeting_intention", member_id)
        for member_id in endpoints
    ]
    pause = _one(events, "pause_after_mutual_interest", None)
    if date is not None:
        if not mutual_yes:
            raise ValueError("date event without two positive responses")
        if date["occurred_day"] < max(event["occurred_day"] for event in responses.values()):
            raise ValueError("date occurs before the positive responses")
    if any(event is not None for event in second_events):
        if date is None or date.get("value") is not True:
            raise ValueError("second intention without a completed date")
        if any(
            event is not None
            and event.get("occurred_day") is not None
            and event["occurred_day"] < date["occurred_day"]
            for event in second_events
        ):
            raise ValueError("second intention occurs before the date")
    if pause is not None:
        if not all(event is not None and event.get("value") == "yes" for event in second_events):
            raise ValueError("pause event without two positive second intentions")
        if pause["occurred_day"] < max(event["observed_day"] for event in second_events):
            raise ValueError("pause occurs before second intentions are observed")


def recorded_yes_by_deadline(introduction, events, member_id):
    """Return whether one endpoint recorded Yes inside its response window."""
    assigned, deadline, endpoints = _validate_introduction(introduction)
    if member_id not in endpoints:
        raise ValueError("response member is not an introduction endpoint")
    validate_event_sequence(introduction, events)
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
    validate_event_sequence(introduction, events)
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
