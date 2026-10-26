"""What the learner side says happened: the output of B against a Lesson."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from instep.lesson.schema import Contract

EventKind = Literal["advance", "skip", "stall", "amount", "not_yet", "frozen", "resume"]

# Kinds that need a claim beyond presence, order and progress (see Lesson.claims()).
NEEDS_CLAIM = {"amount": "amount", "not_yet": "wait_until"}


def needs_claim(kind: str, detail: dict) -> str | None:
    """A not_yet from a stated timer needs only a clock; one from judging the work needs the
    teacher's own viewpoint."""
    if kind == "not_yet" and detail.get("timer"):
        return None
    return NEEDS_CLAIM.get(kind)


class Event(Contract):
    t_s: float = Field(ge=0)
    kind: EventKind
    step_id: str | None = None
    detail: dict[str, Any] = {}
    cue: str | None = None  # what the learner hears, in the teacher's voice where possible
