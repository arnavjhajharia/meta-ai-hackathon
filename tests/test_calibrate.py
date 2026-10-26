"""Calibration on hand-built tutorial measurements (plumbing only)."""

from instep.learner.measure import ClipMeasures
from instep.teacher.calibrate import calibrate
from tests.test_machine import frames, phone_lesson


def clip(seen, hidden=()):
    return ClipMeasures(
        clip="t.mp4", fps=2, width=640, segmenter="fake", frames=frames(60, seen, hidden)
    )


def test_appearance_snaps_step_end_and_marks_out_of_view() -> None:
    lesson = phone_lesson()
    lesson.steps[0].span = None
    lesson.steps[1].span = None
    out, report = calibrate(
        lesson, clip({"mustard_seeds": (11, 60), "curry_leaves": (23, 60)}, hidden=[(40, 45)])
    )
    s0, s1 = out.steps
    assert s0.span.end_s == 12.0  # seen from 11 s, held 1 s
    assert s1.span.end_s == 24.0
    assert s0.span.end_s <= s1.span.start_s
    assert [(sp.start_s, sp.end_s) for sp in out.calibration.out_of_view] == [(40.0, 45.0)]
    assert report.findability["mustard_seeds"] > 0.5
    assert out.provenance.made_by.segmenter == "fake"


def test_unseen_object_keeps_model_times_and_is_reported() -> None:
    lesson = phone_lesson()
    out, report = calibrate(lesson, clip({}))
    assert out.steps[0].span.start_s == lesson.steps[0].span_model.start_s
    assert any("never seen arriving" in i for i in report.issues)
    assert any("almost never found" in i for i in report.issues)
