import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from instep.eval.labels import LabelFile
from instep.eval.learner import score
from instep.eval.teacher import StepReference, consistency, ref_score
from instep.learner.events import Event
from instep.lesson.schema import Lesson

FIXTURES = Path(__file__).parent / "fixtures"


def lesson() -> Lesson:
    return Lesson.model_validate(json.loads((FIXTURES / "lesson_phone_min.json").read_text()))


def test_reference_must_be_confirmed() -> None:
    with pytest.raises(ValidationError):
        StepReference(video="v.mp4", confirmed_by="", steps=[])


def test_ref_score_counts_matches_and_errors() -> None:
    ref = StepReference(
        video="v.mp4",
        confirmed_by="Arnav",
        steps=[
            {"title": "a", "start_s": 9.0, "end_s": 14.0},
            {"title": "b", "start_s": 21.0, "end_s": 27.0},
            {"title": "c", "start_s": 40.0, "end_s": 45.0},
        ],
    )
    s = ref_score(lesson(), ref)
    assert s.recall == pytest.approx(2 / 3, abs=0.01)
    assert s.precision == 1.0
    assert s.within_3s == 1.0


def test_consistency_of_a_lesson_with_itself_is_one() -> None:
    assert consistency(lesson(), lesson()) == 1.0


def test_learner_score() -> None:
    labels = LabelFile(
        recording="x.mp4",
        lesson_id="l",
        confirmed_by="Arnav",
        rows=[
            {"t_s": 10.0, "kind": "advance", "step_id": "a"},
            {"t_s": 30.0, "kind": "skip", "step_id": "b"},
            {"t_s": 31.0, "kind": "advance", "step_id": "c"},
        ],
    )
    events = [
        Event(t_s=11.5, kind="advance", step_id="a"),
        Event(t_s=33.0, kind="skip", step_id="b"),
        Event(t_s=36.0, kind="advance", step_id="c"),
        Event(t_s=50.0, kind="advance", step_id="d"),
    ]
    s = score(events, labels, duration_s=60)
    assert s.advance_within_3s == 0.5
    assert s.false_advances == 1
    assert (s.skips_caught, s.skips_labelled, s.false_skips) == (1, 1, 0)
    assert s.false_events_per_min == 1.0
