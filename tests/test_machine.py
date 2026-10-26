"""Step machine on hand-built measurement sequences (plumbing only; never tune on these)."""

import json
from pathlib import Path

from instep.learner.machine import StepMachine, Tuning, run
from instep.learner.measure import FrameMeasure, ObjectSeen
from instep.lesson.schema import Lesson
from instep.providers.fake import FakeStillJudge

FIXTURES = Path(__file__).parent / "fixtures"
FPS = 2.0


def phone_lesson() -> Lesson:
    return Lesson.model_validate(json.loads((FIXTURES / "lesson_phone_min.json").read_text()))


def frames(duration_s: float, seen: dict[str, tuple[float, float]], hidden=(), hands=(), moving=()):
    """seen: object id -> (from_s, to_s) when it is in the work area."""
    out = []
    for i in range(int(duration_s * FPS)):
        t = i / FPS
        visible = not any(a <= t < b for a, b in hidden)
        objects = {
            oid: ObjectSeen(score=0.9 if visible else 0, in_work_area=visible, coverage=0.1)
            for oid, (a, b) in seen.items()
            if a <= t < b
        }
        objects["pan"] = ObjectSeen(score=0.9, in_work_area=visible, coverage=1.0)
        out.append(
            FrameMeasure(
                t_s=t,
                work_area_visible=visible,
                work_area_box=(0.2, 0.2, 0.8, 0.8) if visible else None,
                objects=objects,
                hands_in_work_area=any(a <= t < b for a, b in hands),
                motion=0.1 if any(a <= t < b for a, b in moving) else 0.0,
            )
        )
    return out


def kinds(events):
    return [(e.kind, e.step_id) for e in events]


def test_clean_attempt_advances_in_order() -> None:
    events, _ = run(
        phone_lesson(),
        frames(30, {"mustard_seeds": (5, 30), "curry_leaves": (15, 30)}),
    )
    assert kinds(events) == [("advance", "add_mustard"), ("advance", "add_curry_leaves")]
    assert 5.5 <= events[0].t_s <= 7.0
    assert events[-1].cue == "That's it, you're done."


def test_flicker_does_not_break_the_hold() -> None:
    seen = frames(20, {"mustard_seeds": (5, 20)})
    for m in seen:
        if m.t_s in (5.5, 6.5):  # detector misses single frames
            m.objects.pop("mustard_seeds")
    events, _ = run(phone_lesson(), seen)
    assert kinds(events)[0] == ("advance", "add_mustard")


def test_skipped_step_is_reported() -> None:
    events, _ = run(phone_lesson(), frames(30, {"curry_leaves": (5, 30)}))
    assert kinds(events) == [("skip", "add_mustard"), ("advance", "add_curry_leaves")]
    assert "skipped" in events[0].cue


def test_looking_away_freezes_and_is_not_progress() -> None:
    events, machine = run(
        phone_lesson(),
        frames(40, {"mustard_seeds": (12, 40)}, hidden=[(4, 11)]),
    )
    assert kinds(events)[:3] == [
        ("frozen", "add_mustard"),
        ("resume", "add_mustard"),
        ("advance", "add_mustard"),
    ]
    assert not any(e.kind == "stall" and e.step_id == "add_mustard" for e in events)


def test_out_of_view_time_does_not_count_towards_a_stall() -> None:
    lesson = phone_lesson()
    tuning = Tuning(stall_min_s=20, stall_factor=0)
    events, _ = run(lesson, frames(30, {}, hidden=[(5, 25)]), tuning=tuning)
    assert not any(e.kind == "stall" for e in events)
    events, _ = run(lesson, frames(30, {}), tuning=tuning)
    assert [e.kind for e in events] == ["stall"]
    assert events[0].detail["replay"] == [9.5, 13.0]


def test_end_state_step_is_judged_only_at_settle_moments() -> None:
    lesson = phone_lesson()
    step = lesson.steps[0]
    step.completion = step.completion.model_copy(
        update={"kind": "end_state", "object": None, "end_state": "seeds in the oil"}
    )
    calls = []

    def decide(still: bytes, end_state: str) -> bool:
        calls.append(still)
        return still == b"10.0"

    judge = FakeStillJudge(decide)
    machine = StepMachine(
        lesson, judge=judge, still_at=lambda t: f"{t:.1f}".encode(), tuning=Tuning(judge_every_s=4)
    )
    for m in frames(14, {}, hands=[(0, 5.5)], moving=[(0, 5.5)]):
        machine.feed(m)
    # hands busy until 5.5 s, still from then on -> judged at 6.0 s, next allowed at 10.0 s
    assert [e.kind for e in machine.events] == ["advance"]
    assert calls == [b"6.0", b"10.0"]
    assert machine.events[0].t_s == 10.0
