"""Strict event interpretation shared by evidence audits.

The simulator emits one event of each required type and member. Rejecting
duplicates keeps a corrupted or hand-edited evidence file from silently
changing an outcome. Boundary checks use the published inclusive windows.
"""
from __future__ import annotations


def _one(events, event_name, member_id=None):
    selected = [
        event for event in events
        if event.get("event") == event_name
        and (member_id is None or event.get("member_id") == member_id)
    ]
    if len(selected) > 1:
        label = event_name if member_id is None else f"{event_name}/{member_id}"
        raise ValueError(f"duplicate outcome event: {label}")
    return selected[0] if selected else None


def recorded_yes_by_deadline(introduction, events, member_id):
    """Return whether one endpoint recorded Yes inside its response window."""
    event = _one(events, "introduction_response", member_id)
    if event is None or event.get("value") != "yes":
        return False
    occurred = event.get("occurred_day")
    observed = event.get("observed_day")
    assigned = introduction["assigned_day"]
    deadline = introduction["response_deadline_day"]
    return (
        isinstance(occurred, int)
        and isinstance(observed, int)
        and assigned <= occurred <= deadline
        and occurred <= observed <= deadline
    )


def classify_funnel(introduction, events):
    """Classify mutual response, date and MSMI without collapsing stages."""
    endpoints = (introduction["user_a"], introduction["user_b"])
    mutual = all(
        recorded_yes_by_deadline(introduction, events, member_id)
        for member_id in endpoints
    )
    date = _one(events, "date_happened")
    assigned = introduction["assigned_day"]
    date_day = date.get("occurred_day") if date and date.get("value") is True else None
    dated = (
        mutual
        and isinstance(date_day, int)
        and assigned <= date_day <= assigned + 30
        and isinstance(date.get("observed_day"), int)
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
        isinstance(occurred, int)
        and isinstance(observed, int)
        and date_day <= occurred <= date_day + 3
        and occurred <= observed <= date_day + 3
    )
