"""A' teacher recording -> draft Lesson: frames + transcript -> one model call -> checked Lesson."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from instep import __version__
from instep.lesson.schema import (
    EM_DASH,
    Completion,
    Lesson,
    MadeBy,
    Provenance,
    RecordingRef,
    Span,
    Step,
    Tip,
    TrackedObject,
    TranscriptSegment,
)
from instep.media.frames import VideoInfo, frame_at, keyframe_times, scene_cuts, to_jpeg
from instep.providers.base import (
    DraftLesson,
    DraftRequest,
    TimedImage,
    Transcript,
    Understander,
)
from instep.teacher.ground import ground_tip

PROMPTS = Path(__file__).parent / "prompts"


@dataclass(frozen=True)
class DraftSettings:
    prompt_version: str = "draft_v1"
    every_s: float = 2.0
    max_frames: int = 120
    width: int = 512
    use_transcript: bool = True

    @property
    def label(self) -> str:
        t = "tx" if self.use_transcript else "notx"
        return f"{self.prompt_version}-{self.every_s:g}s-{self.max_frames}f-{self.width}w-{t}"


@dataclass
class DraftOutcome:
    lesson: Lesson
    draft: DraftLesson
    issues: list[str] = field(default_factory=list)
    model: str = ""
    usage: dict[str, int] = field(default_factory=dict)


def build_request(
    video: Path, info: VideoInfo, transcript: Transcript | None, settings: DraftSettings
) -> DraftRequest:
    cuts = scene_cuts(video)
    times = keyframe_times(info.duration_s, cuts, settings.every_s, settings.max_frames)
    frames = [TimedImage(t, to_jpeg(frame_at(video, t, settings.width), 75)) for t in times]
    return DraftRequest(
        frames=frames,
        transcript=transcript if settings.use_transcript else None,
        duration_s=info.duration_s,
        prompt_version=settings.prompt_version,
        instructions=(PROMPTS / f"{settings.prompt_version}.md").read_text(),
        cuts=[round(c, 1) for c in cuts],
    )


def draft_lesson(
    video: Path,
    info: VideoInfo,
    recording: RecordingRef,
    transcript: Transcript | None,
    understander: Understander,
    settings: DraftSettings,
    transcriber_name: str,
    segmenter_name: str = "none",
) -> DraftOutcome:
    request = build_request(video, info, transcript, settings)
    result = understander.draft_lesson(request)
    lesson, issues = to_lesson(
        result.draft,
        recording=recording,
        transcript=transcript,
        made_by=MadeBy(
            understanding=f"{understander.name}:{result.model}:{settings.label}",
            segmenter=segmenter_name,
            transcriber=transcriber_name,
            pipeline_version=__version__,
            created_at=datetime.now(UTC),
        ),
        frame_times=[f.t_s for f in request.frames],
    )
    return DraftOutcome(lesson, result.draft, issues, result.model, result.usage)


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_") or "x"


def _clean(text: str) -> str:
    return text.replace(EM_DASH, ", ").replace(" ,", ",").strip()


def _area(raw: str | None, objects: dict, default: str, sid: str, issues: list[str]) -> str | None:
    if not raw:
        return None
    area = _slug(raw)
    if area not in objects:
        issues.append(f"step {sid!r} work area {area!r} unknown; using the main one")
        return None
    return None if area == default else area


def to_lesson(
    draft: DraftLesson,
    recording: RecordingRef,
    transcript: Transcript | None,
    made_by: MadeBy,
    frame_times: list[float],
) -> tuple[Lesson, list[str]]:
    """Map the model's plain draft onto the strict schema, repairing what can be repaired and
    reporting every repair. A draft that needs many repairs is a bad draft."""
    issues: list[str] = []
    duration = recording.duration_s

    objects: dict[str, TrackedObject] = {}
    for o in draft.objects:
        oid = _slug(o.id)
        if oid in objects:
            issues.append(f"duplicate object {oid!r} dropped")
            continue
        objects[oid] = TrackedObject(id=oid, prompt=o.prompt.lower().strip(), role=o.role)
    for o in draft.objects:
        oid = _slug(o.id)
        objects[oid].confusable_with = [
            _slug(c) for c in o.confusable_with if _slug(c) in objects and _slug(c) != oid
        ]

    work_area = _slug(draft.work_area_object)
    if work_area not in objects:
        issues.append(f"work area {work_area!r} not among objects; added it")
        objects[work_area] = TrackedObject(
            id=work_area, prompt=draft.work_area_object.replace("_", " "), role="work_area"
        )
    if objects[work_area].role != "work_area":
        objects[work_area].role = "work_area"
    step_areas = {_slug(s.work_area) for s in draft.steps if s.work_area}
    for oid, o in objects.items():
        if oid in step_areas and o.role != "work_area":
            o.role = "work_area"
        if o.role == "work_area" and oid != work_area and oid not in step_areas:
            issues.append(f"second work area {oid!r} used by no step; demoted to container")
            o.role = "container"

    steps: list[Step] = []
    seen_ids: set[str] = set()
    last_end = 0.0
    for d in sorted(draft.steps, key=lambda s: s.start_s):
        sid = _slug(d.id)
        while sid in seen_ids:
            sid += "_b"
        seen_ids.add(sid)
        start = min(max(d.start_s, 0.0), duration - 0.2)
        end = min(max(d.end_s, start + 0.2), duration)
        if start < last_end:
            issues.append(
                f"step {sid!r} overlapped the previous one; start moved to {last_end:.1f}s"
            )
            start = last_end
            end = max(end, start + 0.2)
        if end > duration:
            issues.append(f"step {sid!r} ran past the end; dropped")
            continue
        last_end = end

        refs = [_slug(r) for r in d.objects]
        unknown = [r for r in refs if r not in objects]
        if unknown:
            issues.append(f"step {sid!r} referenced unknown objects {unknown}; removed")
        refs = [r for r in refs if r in objects]

        kind = d.completion_kind
        obj = _slug(d.completion_object) if d.completion_object else None
        if kind != "end_state" and (obj is None or obj not in objects):
            issues.append(f"step {sid!r} {kind} without a known object; now end_state")
            kind, obj = "end_state", None
        if kind == "end_state":
            obj = None
        if obj and obj not in refs:
            refs.append(obj)

        ref_t = d.reference_frame_s
        if frame_times:
            nearest = min(frame_times, key=lambda t: abs(t - ref_t))
            if abs(nearest - ref_t) > 0.6:
                issues.append(f"step {sid!r} reference frame {ref_t:.1f}s is not a given frame")
            ref_t = nearest
        ref_t = min(max(ref_t, 0.0), duration)

        tips = []
        for t in d.tips:
            kept, issue = ground_tip(t, transcript)
            if issue:
                issues.append(f"step {sid!r}: {issue}")
            if kept:
                tips.append(
                    Tip(
                        text=_clean(kept.text),
                        quote=kept.quote if kept.source != "action" else None,
                        quote_language=kept.quote_language if kept.source != "action" else None,
                        source=kept.source,
                        at_s=min(max(kept.at_s, 0.0), duration),
                    )
                )

        steps.append(
            Step(
                id=sid,
                index=len(steps),
                title=_clean(d.title),
                instruction=_clean(d.instruction),
                objects=refs,
                completion=Completion(
                    kind=kind,
                    object=obj,
                    end_state=_clean(d.end_state) or None,
                    reference_frame_s=ref_t,
                ),
                span_model=Span(start_s=start, end_s=end),
                tips=tips,
                optional=d.optional,
                wait_s=d.wait_s if d.wait_s and d.wait_s > 0 else None,
                work_area=_area(d.work_area, objects, work_area, sid, issues),
            )
        )

    segments = []
    if transcript:
        segments = [
            TranscriptSegment(
                start_s=min(s.start_s, duration),
                end_s=min(max(s.end_s, s.start_s + 0.01), duration),
                text=s.text,
                language=transcript.language,
            )
            for s in transcript.segments
            if s.start_s < duration
        ]

    lesson = Lesson(
        id=f"{_slug(draft.task).replace('_', '-')}-{Path(recording.path).stem.split('_')[-1]}",
        title=_clean(draft.title),
        task=draft.task,
        language=draft.language if draft.language != "none" else None,
        provenance=Provenance(
            teacher_device="phone",
            viewpoint="third_person",
            authored="pipeline",
            recording=recording,
            made_by=made_by,
        ),
        objects=list(objects.values()),
        work_area_object=work_area,
        steps=steps,
        transcript=segments,
    )
    return lesson, issues
