"""Step logic: frame measurements in, events out. Plain code, no model in the loop.

The reasoning model is reached only through ``judge`` at settle moments (hands out of the work
area and the scene still), on one still, and never more often than ``judge_every_s``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from instep.learner.events import NEEDS_CLAIM, Event
from instep.learner.measure import FrameMeasure
from instep.lesson.schema import Lesson, Step
from instep.providers.base import StillJudge


@dataclass(frozen=True)
class Tuning:
    present_score: float = 0.35  # detection score that counts as "seen"
    leak: float = 0.5  # evidence decays at this rate while unseen (absorbs detector flicker)
    skip_hold_factor: float = 2.0  # later-step evidence must hold this many times longer
    coverage_delta: float = 0.15  # coverage change that counts for coverage_change steps
    dropout_s: float = 1.5  # work area unseen this long -> frozen
    settle_motion: float = 0.025  # below this motion the scene counts as still
    settle_s: float = 1.0  # still for this long, hands out -> settle moment
    judge_every_s: float = 4.0
    min_step_s: float = 2.0  # never judge a step this soon after it became current
    object_step_judge_after_s: float = 10.0  # object steps fall back to the judge after this
    skip_judge_after_s: float = 12.0  # judge the next end_state step for a skip after this
    skip_confidence: float = 0.75
    done_confidence: float = 0.6
    stall_min_s: float = 25.0
    stall_factor: float = 2.5  # times the tutorial step length


@dataclass
class _Evidence:
    run_s: float = 0.0  # leaky time seen
    absent_s: float = 0.0  # continuous time unseen
    last: bool = False

    def update(self, seen: bool, dt: float, leak: float) -> None:
        self.run_s = self.run_s + dt if seen else max(0.0, self.run_s - dt * leak)
        self.absent_s = 0.0 if seen else self.absent_s + dt
        self.last = seen


@dataclass
class StepMachine:
    lesson: Lesson
    tuning: Tuning = field(default_factory=Tuning)
    judge: StillJudge | None = None
    still_at: Callable[[float], bytes] | None = None  # learner still at time t
    reference_for: Callable[[Step], bytes | None] | None = None  # teacher still for a step

    def __post_init__(self) -> None:
        self.k = 0
        self.events: list[Event] = []
        self.frozen = False
        self.missing_s = 0.0
        self.active_s = 0.0  # in-view time in the current step
        self.since_progress_s = 0.0
        self.settle_run_s = 0.0
        self.last_judge_t = -1e9
        self.last_t: float | None = None
        self.evidence: dict[str, _Evidence] = {o.id: _Evidence() for o in self.lesson.objects}
        self.baseline: dict[str, tuple[bool, float]] | None = None
        self.claims = self.lesson.claims()
        self.judge_calls = 0

    # ---------- public ----------

    @property
    def done(self) -> bool:
        return self.k >= len(self.lesson.steps)

    @property
    def current(self) -> Step | None:
        return None if self.done else self.lesson.steps[self.k]

    def feed(self, m: FrameMeasure) -> list[Event]:
        """Process one frame measurement; return the events it caused."""
        start = len(self.events)
        dt = 0.0 if self.last_t is None else max(0.0, m.t_s - self.last_t)
        self.last_t = m.t_s
        if self.done:
            return []
        if not self._visibility(m, dt):
            return self.events[start:]

        t = self.tuning
        for oid, ev in self.evidence.items():
            seen = m.objects.get(oid)
            ev.update(
                bool(seen and seen.in_work_area and seen.score >= t.present_score), dt, t.leak
            )
        if self.baseline is None:
            self.baseline = self._snapshot(m)

        self.active_s += dt
        self.since_progress_s += dt
        still = not m.hands_in_work_area and m.motion < t.settle_motion
        self.settle_run_s = self.settle_run_s + dt if still else 0.0

        if not self._object_progress(m):
            self._judge_progress(m)
        self._stall(m)
        return self.events[start:]

    def finish(self, t_s: float) -> list[Event]:
        """End of the recording: nothing more to decide."""
        return []

    # ---------- visibility: not seeing is not evidence ----------

    def _visibility(self, m: FrameMeasure, dt: float) -> bool:
        if m.work_area_visible:
            self.missing_s = 0.0
            if self.frozen:
                self.frozen = False
                self._emit(m.t_s, "resume", self.current)
            return True
        self.missing_s += dt
        if not self.frozen and self.missing_s >= self.tuning.dropout_s:
            self.frozen = True
            self._emit(m.t_s, "frozen", self.current)
        # a short dropout is carried through as if nothing happened; timers do not advance
        return False

    # ---------- object evidence ----------

    def _snapshot(self, m: FrameMeasure) -> dict[str, tuple[bool, float]]:
        out = {}
        for oid in self.evidence:
            seen = m.objects.get(oid)
            present = bool(seen and seen.in_work_area and seen.score >= self.tuning.present_score)
            out[oid] = (present, seen.coverage if seen else 0.0)
        return out

    def _step_evidence(self, step: Step, m: FrameMeasure, hold_factor: float = 1.0) -> bool:
        c = step.completion
        if c.object is None or self.baseline is None:
            return False
        hold = max(c.min_hold_s, 0.5) * hold_factor
        ev = self.evidence[c.object]
        was_present, was_cov = self.baseline[c.object]
        seen = m.objects.get(c.object)
        if c.kind == "appears_in_work_area":
            return not was_present and ev.run_s >= hold
        if c.kind == "leaves_work_area":
            return was_present and ev.absent_s >= hold
        if c.kind == "coverage_change":
            return bool(seen) and abs(seen.coverage - was_cov) >= self.tuning.coverage_delta
        return False

    def _object_progress(self, m: FrameMeasure) -> bool:
        steps = self.lesson.steps
        cur = steps[self.k]
        if self._step_evidence(cur, m):
            self._advance(m, reason="object")
            return True
        # evidence for a later step while the current one is not done: a skip
        for j in range(self.k + 1, len(steps)):
            if self._step_evidence(steps[j], m, self.tuning.skip_hold_factor):
                skipped = [s for s in steps[self.k : j] if not s.optional]
                for s in skipped:
                    self._emit(
                        m.t_s,
                        "skip",
                        s,
                        cue=f"Wait, you skipped a step. {s.instruction}",
                        detail={"evidence_for": steps[j].id},
                    )
                self.k = j
                self._advance(m, reason="object_after_skip", quiet_skip=not skipped)
                return True
        return False

    # ---------- slow path: one still at a settle moment ----------

    def _judge_progress(self, m: FrameMeasure) -> None:
        t = self.tuning
        cur = self.current
        if cur is None or self.judge is None or self.still_at is None:
            return
        if self.settle_run_s < t.settle_s or m.t_s - self.last_judge_t < t.judge_every_s:
            return
        if self.active_s < t.min_step_s or not cur.completion.end_state:
            return
        if cur.completion.kind != "end_state" and self.active_s < t.object_step_judge_after_s:
            return
        self.last_judge_t = m.t_s
        still = self.still_at(m.t_s)
        verdict = self._ask(cur, still)
        if verdict is None:
            return
        if verdict.done and verdict.confidence >= t.done_confidence:
            self._advance(m, reason="judge", detail={"confidence": verdict.confidence})
            return
        # maybe they already did the next shape-change step (an origami fold skipped)
        nxt = self.lesson.steps[self.k + 1] if self.k + 1 < len(self.lesson.steps) else None
        if (
            nxt is not None
            and nxt.completion.kind == "end_state"
            and self.active_s >= t.skip_judge_after_s
        ):
            v2 = self._ask(nxt, still)
            if v2 and v2.done and v2.confidence >= t.skip_confidence:
                if not cur.optional:
                    self._emit(
                        m.t_s, "skip", cur, cue=f"Wait, you skipped a step. {cur.instruction}"
                    )
                self.k += 1
                self._advance(m, reason="judge_after_skip", quiet_skip=True)

    def _ask(self, step: Step, still: bytes):
        assert self.judge is not None
        reference = self.reference_for(step) if self.reference_for else None
        self.judge_calls += 1
        verdict = self.judge.judge(still, reference, step.completion.end_state or "", step.title)
        return verdict if verdict.visible else None

    # ---------- stalls ----------

    def _stall(self, m: FrameMeasure) -> None:
        cur = self.current
        if cur is None:
            return
        span = cur.best_span
        teacher_s = (span.end_s - span.start_s) if span else 0.0
        limit = max(self.tuning.stall_min_s, self.tuning.stall_factor * teacher_s)
        if self.since_progress_s >= limit:
            tip = next((tip.text for tip in cur.tips), None)
            cue = f"Take your time. {tip or cur.instruction}"
            detail = {"replay": [span.start_s, span.end_s]} if span else {}
            self._emit(m.t_s, "stall", cur, cue=cue, detail=detail)
            self.since_progress_s = 0.0

    # ---------- bookkeeping ----------

    def _advance(self, m: FrameMeasure, reason: str, quiet_skip: bool = False, detail=None):
        finished = self.lesson.steps[self.k]
        self.k += 1
        nxt = self.current
        cue = f"{nxt.title}. {nxt.instruction}" if nxt else "That's it, you're done."
        self._emit(m.t_s, "advance", finished, cue=cue, detail={"reason": reason, **(detail or {})})
        self.active_s = 0.0
        self.since_progress_s = 0.0
        self.settle_run_s = 0.0
        self.baseline = self._snapshot(m)
        for ev in self.evidence.values():
            ev.run_s = 0.0
            ev.absent_s = 0.0

    def _emit(self, t_s, kind, step, cue=None, detail=None) -> None:
        needed = NEEDS_CLAIM.get(kind)
        if needed and needed not in self.claims:
            return  # this recording cannot support that claim
        self.events.append(
            Event(
                t_s=t_s, kind=kind, step_id=step.id if step else None, cue=cue, detail=detail or {}
            )
        )


def run(lesson: Lesson, measures: list[FrameMeasure], **kwargs) -> tuple[list[Event], StepMachine]:
    machine = StepMachine(lesson, **kwargs)
    for m in measures:
        machine.feed(m)
    return machine.events, machine
