"""Lesson schema v1.

A Lesson is one task, as a teacher did it, in a form every mode can read. It records how it was
made (provenance) so downstream code knows which claims the recording supports.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

SCHEMA_VERSION = "1"
EM_DASH = "—"


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Claim(StrEnum):
    presence = "presence"
    order = "order"
    progress = "progress"
    amount = "amount"
    wait_until = "wait_until"


COARSE_CLAIMS = frozenset({Claim.presence, Claim.order, Claim.progress})


class Span(Contract):
    start_s: float = Field(ge=0)
    end_s: float

    @model_validator(mode="after")
    def _positive_length(self) -> Self:
        if self.end_s <= self.start_s:
            raise ValueError(f"end_s ({self.end_s}) must be after start_s ({self.start_s})")
        return self


class RecordingRef(Contract):
    path: str
    source_url: str | None = None
    sha256: str
    duration_s: float = Field(gt=0)
    fps: float = Field(gt=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)


class MadeBy(Contract):
    understanding: str
    segmenter: str
    transcriber: str
    pipeline_version: str
    created_at: datetime


class Provenance(Contract):
    teacher_device: Literal["glasses", "phone"]
    viewpoint: Literal["first_person", "third_person"]
    authored: Literal["hand_written", "pipeline"]
    stand_in: bool = False
    recording: RecordingRef | None = None
    made_by: MadeBy | None = None

    @model_validator(mode="after")
    def _pipeline_has_sources(self) -> Self:
        if self.authored == "pipeline":
            if self.recording is None:
                raise ValueError("a pipeline lesson needs a recording")
            if self.made_by is None:
                raise ValueError("a pipeline lesson needs made_by")
        return self


class TrackedObject(Contract):
    id: str
    prompt: str = Field(min_length=1)
    role: Literal["work_area", "ingredient", "material", "part", "tool", "container", "hand"]
    confusable_with: list[str] = []


OBJECT_KINDS = {"appears_in_work_area", "leaves_work_area", "coverage_change"}


class Completion(Contract):
    """How the learner side knows a step is finished.

    Object kinds are watched every frame by the segmenter. ``end_state`` is for steps where
    nothing new appears and only the shape or arrangement changes (a fold, a wrap, a knot): it
    is judged from one still at a settle moment, against the teacher's reference frame. Any
    kind may carry ``end_state`` text as a fallback description for that still check.
    """

    kind: Literal[
        "appears_in_work_area", "leaves_work_area", "coverage_change", "end_state", "manual"
    ]
    object: str | None = None
    end_state: str | None = None  # what the work looks like when the step is done
    reference_frame_s: float | None = Field(default=None, ge=0)  # teacher frame showing it
    min_hold_s: float = Field(default=1.0, ge=0)

    @model_validator(mode="after")
    def _has_what_it_needs(self) -> Self:
        if self.kind in OBJECT_KINDS and not self.object:
            raise ValueError(f"completion kind {self.kind} needs an object")
        if self.kind == "end_state" and not self.end_state:
            raise ValueError("completion kind end_state needs end_state text")
        return self


class WaitUntil(Contract):
    condition: str
    still_checkable: bool
    reference_frame_s: float | None = Field(default=None, ge=0)
    cue_not_yet: str


class Amount(Contract):
    object: str
    measure: Literal["work_area_fraction"] = "work_area_fraction"
    teacher_value: float | None = Field(default=None, ge=0, le=1)
    tolerance: float = Field(gt=0)


class Tip(Contract):
    text: str
    quote: str | None = None  # verbatim, in the language the teacher spoke
    quote_language: str | None = None  # ISO 639-1, e.g. "hi"
    source: Literal["speech", "caption", "action"]  # said it, wrote it on screen, or showed it
    at_s: float = Field(ge=0)

    @model_validator(mode="after")
    def _words_are_quoted(self) -> Self:
        if self.source in ("speech", "caption") and not self.quote:
            raise ValueError(f"a {self.source} tip needs the teacher's quote")
        return self


class Step(Contract):
    id: str
    index: int = Field(ge=0)
    title: str
    instruction: str
    objects: list[str]
    completion: Completion
    span_model: Span | None = None
    span: Span | None = None
    wait_until: WaitUntil | None = None
    amount: Amount | None = None
    tips: list[Tip] = []
    optional: bool = False
    # a timed wait the teacher states ("leave the glue for 5 minutes"): needs only a clock, so
    # every mode may use it, unlike wait_until which needs the teacher's own viewpoint
    wait_s: float | None = Field(default=None, gt=0)
    # where this step happens when it is not the lesson's main work area (the wok before the
    # pan); must be an object with role work_area
    work_area: str | None = None

    def area(self, lesson_default: str) -> str:
        return self.work_area or lesson_default

    @property
    def best_span(self) -> Span | None:
        """The snapped span when there is one, otherwise the model's rough one."""
        return self.span or self.span_model


class TranscriptSegment(Contract):
    start_s: float = Field(ge=0)
    end_s: float
    text: str
    speaker: str = "teacher"
    language: str | None = None


class Calibration(Contract):
    ran_at: datetime
    segmenter: str
    out_of_view: list[Span] = []


class Lesson(Contract):
    schema_version: Literal["1"] = SCHEMA_VERSION
    id: str
    title: str
    task: str | None = None  # slug shared by lessons and attempts of the same task
    language: str | None = None  # main spoken language of the recording
    provenance: Provenance
    objects: list[TrackedObject]
    work_area_object: str
    steps: list[Step] = Field(min_length=1)
    transcript: list[TranscriptSegment] = []
    calibration: Calibration | None = None

    def claims(self) -> frozenset[Claim]:
        """What this recording lets downstream code judge. Amounts and "wait until" need the
        teacher's own first-person view."""
        p = self.provenance
        if p.teacher_device == "glasses" and p.viewpoint == "first_person":
            return frozenset(Claim)
        return COARSE_CLAIMS

    def object(self, object_id: str) -> TrackedObject:
        return next(o for o in self.objects if o.id == object_id)

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        self._check_ids()
        self._check_references()
        self._check_steps()
        self._check_claims()
        self._check_times()
        self._check_text()
        return self

    def _check_ids(self) -> None:
        for kind, ids in (
            ("object", [o.id for o in self.objects]),
            ("step", [s.id for s in self.steps]),
        ):
            seen: set[str] = set()
            for i in ids:
                if i in seen:
                    raise ValueError(f"duplicate {kind} id: {i!r}")
                seen.add(i)

    def _check_references(self) -> None:
        known = {o.id for o in self.objects}

        def need(ref: str, where: str) -> None:
            if ref not in known:
                raise ValueError(f"{where} refers to unknown object {ref!r}")

        need(self.work_area_object, "work_area_object")
        if self.object(self.work_area_object).role != "work_area":
            raise ValueError(f"work_area_object {self.work_area_object!r} must have role work_area")
        for o in self.objects:
            for other in o.confusable_with:
                need(other, f"object {o.id!r} confusable_with")
        for s in self.steps:
            for ref in s.objects:
                need(ref, f"step {s.id!r} objects")
            if s.completion.object:
                need(s.completion.object, f"step {s.id!r} completion")
            if s.work_area:
                need(s.work_area, f"step {s.id!r} work_area")
                if self.object(s.work_area).role != "work_area":
                    raise ValueError(f"step {s.id!r} work_area {s.work_area!r} is not a work area")
            if s.amount:
                need(s.amount.object, f"step {s.id!r} amount")

    def _check_steps(self) -> None:
        previous: Step | None = None
        for position, s in enumerate(self.steps):
            if s.index != position:
                raise ValueError(f"step {s.id!r} has index {s.index}, expected {position}")
            span = s.best_span
            if previous and span and (prev := previous.best_span):
                if span.start_s <= prev.start_s:
                    raise ValueError(
                        f"steps out of order: {s.id!r} starts at {span.start_s}s, "
                        f"not after {previous.id!r} at {prev.start_s}s"
                    )
            previous = s

    def _check_claims(self) -> None:
        allowed = self.claims()
        for s in self.steps:
            if s.amount and Claim.amount not in allowed:
                raise ValueError(
                    f"step {s.id!r} has an amount, but this recording only supports "
                    f"{', '.join(sorted(allowed))} (amounts need a first-person glasses"
                    " teacher)"
                )
            if s.wait_until and Claim.wait_until not in allowed:
                raise ValueError(
                    f"step {s.id!r} has a wait_until, but this recording only supports "
                    f"{', '.join(sorted(allowed))} (wait_until needs a first-person glasses"
                    " teacher)"
                )

    def _check_times(self) -> None:
        recording = self.provenance.recording
        if recording is None:
            return
        limit = recording.duration_s

        def within(t: float, where: str) -> None:
            if t > limit:
                raise ValueError(f"{where} at {t}s is past the end of the recording ({limit}s)")

        for s in self.steps:
            for name, span in (("span", s.span), ("span_model", s.span_model)):
                if span:
                    within(span.end_s, f"step {s.id!r} {name}")
            for tip in s.tips:
                within(tip.at_s, f"step {s.id!r} tip")
            if s.completion.reference_frame_s is not None:
                within(s.completion.reference_frame_s, f"step {s.id!r} reference frame")
            if s.wait_until and s.wait_until.reference_frame_s is not None:
                within(s.wait_until.reference_frame_s, f"step {s.id!r} wait_until")
        for seg in self.transcript:
            within(seg.end_s, "transcript segment")
        if self.calibration:
            for span in self.calibration.out_of_view:
                within(span.end_s, "out_of_view span")

    def _check_text(self) -> None:
        """Words people hear or read never use em dashes."""
        texts = [("title", self.title)]
        for s in self.steps:
            texts += [
                (f"step {s.id!r} title", s.title),
                (f"step {s.id!r} instruction", s.instruction),
            ]
            texts += [(f"step {s.id!r} tip", t.text) for t in s.tips]
            if s.completion.end_state:
                texts.append((f"step {s.id!r} end_state", s.completion.end_state))
            if s.wait_until:
                texts += [
                    (f"step {s.id!r} condition", s.wait_until.condition),
                    (f"step {s.id!r} cue_not_yet", s.wait_until.cue_not_yet),
                ]
        for where, text in texts:
            if EM_DASH in text:
                raise ValueError(f"{where} contains an em dash: {text!r}")
