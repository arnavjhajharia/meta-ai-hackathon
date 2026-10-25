"""Hand labels for a learner recording. Only a human writes these, and only after confirming."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import Field

from instep.learner.events import EventKind
from instep.lesson.schema import Contract


class LabelRow(Contract):
    t_s: float = Field(ge=0)
    kind: EventKind
    step_id: str | None = None
    note: str = ""


class LabelFile(Contract):
    recording: str
    lesson_id: str
    confirmed_by: str = Field(min_length=1)  # the human who checked every row
    rows: list[LabelRow]


def load_labels(path: Path) -> LabelFile:
    """Refuses a file nobody confirmed: unconfirmed labels make every eval meaningless."""
    return LabelFile.model_validate(json.loads(Path(path).read_text()))
