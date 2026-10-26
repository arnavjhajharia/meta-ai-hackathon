"""The teacher is the first learner: snap model times to what the segmenter saw in the tutorial.

Reads the same per-frame measurements the learner side uses. For A' (phone) tutorials the claims
stay coarse: this only moves step boundaries, finds where the work area is out of view (cut to a
face, B-roll), and checks that each object prompt is findable at all.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from instep.learner.measure import ClipMeasures, FrameMeasure
from instep.lesson.schema import Calibration, Lesson, Span

PRESENT = 0.35
MIN_OUT_OF_VIEW_S = 2.0
SNAP_WINDOW_S = 6.0
HOLD_S = 1.0


@dataclass
class CalibrationReport:
    findability: dict[str, float] = field(default_factory=dict)  # object id -> share of frames
    snapped: dict[str, tuple[float, float]] = field(default_factory=dict)  # step -> (old, new)
    issues: list[str] = field(default_factory=list)
    out_of_view_share: float = 0.0


def _present(m: FrameMeasure, oid: str) -> bool:
    seen = m.objects.get(oid)
    return bool(seen and seen.in_work_area and seen.score >= PRESENT)


def out_of_view_spans(frames: list[FrameMeasure]) -> list[Span]:
    spans, start = [], None
    for m in frames:
        if not m.work_area_visible and start is None:
            start = m.t_s
        elif m.work_area_visible and start is not None:
            if m.t_s - start >= MIN_OUT_OF_VIEW_S:
                spans.append(Span(start_s=start, end_s=m.t_s))
            start = None
    if start is not None and frames and frames[-1].t_s - start >= MIN_OUT_OF_VIEW_S:
        spans.append(Span(start_s=start, end_s=frames[-1].t_s + 0.01))
    return spans


def first_lasting_appearance(frames: list[FrameMeasure], oid: str, lo: float, hi: float):
    run_start = None
    for m in frames:
        if m.t_s < lo or m.t_s > hi:
            continue
        if _present(m, oid):
            run_start = m.t_s if run_start is None else run_start
            if m.t_s - run_start >= HOLD_S:
                return run_start
        else:
            run_start = None
    return None


def calibrate(lesson: Lesson, measures: ClipMeasures) -> tuple[Lesson, CalibrationReport]:
    frames = measures.frames
    report = CalibrationReport()
    duration = lesson.provenance.recording.duration_s if lesson.provenance.recording else 1e9

    for o in lesson.objects:
        if o.id == lesson.work_area_object:
            share = sum(m.work_area_visible for m in frames) / max(1, len(frames))
        else:
            spans = [s.best_span for s in lesson.steps if o.id in s.objects and s.best_span]
            inside = [
                m for m in frames if any(sp.start_s - 2 <= m.t_s <= sp.end_s + 4 for sp in spans)
            ]
            pool = inside or frames
            share = sum(
                (m.objects.get(o.id).score if m.objects.get(o.id) else 0) >= PRESENT for m in pool
            ) / max(1, len(pool))
        report.findability[o.id] = round(share, 3)
        if share < 0.05:
            report.issues.append(
                f"object {o.id!r} ({o.prompt!r}) almost never found by the segmenter"
            )

    steps = [s.model_copy(deep=True) for s in lesson.steps]
    prev_end = 0.0
    for i, s in enumerate(steps):
        model = s.span_model or s.span
        if model is None:
            continue
        start, end = model.start_s, model.end_s
        c = s.completion
        if c.kind == "appears_in_work_area" and c.object:
            seen_at = first_lasting_appearance(
                frames, c.object, max(prev_end, start - SNAP_WINDOW_S), end + SNAP_WINDOW_S
            )
            if seen_at is None:
                report.issues.append(
                    f"step {s.id!r}: {c.object!r} never seen arriving; kept model times"
                )
            else:
                new_end = min(duration, max(seen_at + HOLD_S, prev_end + 0.4))
                new_start = min(start, new_end - 0.2)
                report.snapped[s.id] = (end, new_end)
                start, end = max(prev_end, new_start), new_end
        nxt = steps[i + 1].span_model if i + 1 < len(steps) else None
        if nxt and end > nxt.start_s and c.kind == "appears_in_work_area":
            end = max(start + 0.2, min(end, nxt.end_s - 0.2))
        start = max(start, prev_end)
        end = max(end, start + 0.2)
        s.span = Span(start_s=round(start, 2), end_s=round(min(end, duration), 2))
        prev_end = s.span.end_s

    oov = out_of_view_spans(frames)
    report.out_of_view_share = round(
        sum(sp.end_s - sp.start_s for sp in oov) / max(1e-6, duration if duration < 1e8 else 1), 3
    )
    data = lesson.model_dump()
    data["steps"] = [s.model_dump() for s in steps]
    data["calibration"] = Calibration(
        ran_at=datetime.now(UTC), segmenter=measures.segmenter, out_of_view=oov
    ).model_dump()
    if data["provenance"]["made_by"]:
        data["provenance"]["made_by"]["segmenter"] = measures.segmenter
    return Lesson.model_validate(data), report
