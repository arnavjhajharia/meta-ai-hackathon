"""InStep command line.

python -m instep.cli lesson <tutorial.mp4> [--variant V] [--no-calibrate] [--publish]
python -m instep.cli learn <attempt.mp4> <lesson.json> [--no-judge]
python -m instep.cli grid <video.mp4> [--every 1.0]
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from instep import cache
from instep.config import ROOT, Config
from instep.lesson.io import load_lesson, save_lesson
from instep.lesson.schema import Lesson, RecordingRef, Step
from instep.media.frames import frame_at, probe, read_frames, to_jpeg
from instep.providers import registry

RUNS = ROOT / "runs"
LESSONS = ROOT / "data" / "lessons" / "generated"
TUTORIAL_FPS = 1.0
LEARNER_FPS = 2.0
SEG_WIDTH = 640


def parse_variant(text: str):
    """prompt:every_s:max_frames:width:tx|notx, e.g. draft_v1:2:120:512:tx"""
    from instep.teacher.draft import DraftSettings

    p, every, n, w, tx = text.split(":")
    return DraftSettings(p, float(every), int(n), int(w), tx == "tx")


def manifest_row(video: Path) -> dict:
    manifest = ROOT / "data" / "tutorials.json"
    if manifest.exists():
        for row in json.loads(manifest.read_text()):
            if row.get("file") == video.name:
                return row
    return {}


def transcribe_if_spoken(video: Path, cfg: Config):
    """Music-only tutorials are not transcribed: Whisper invents words over music."""
    if not probe(video).has_audio or manifest_row(video).get("has_narration") is False:
        return None
    return registry.transcriber(cfg).transcribe(video)


def recording_ref(video: Path) -> RecordingRef:
    info = probe(video)
    url = None
    manifest = ROOT / "data" / "tutorials.json"
    if manifest.exists():
        for row in json.loads(manifest.read_text()):
            if row.get("file") == video.name:
                url = row.get("url")
    return RecordingRef(
        path=str(video.relative_to(ROOT)) if video.is_relative_to(ROOT) else str(video),
        source_url=url,
        sha256=cache.file_sha256(video),
        duration_s=info.duration_s,
        fps=info.fps,
        width=info.width,
        height=info.height,
    )


def build_lesson(
    video: Path, settings, calibrate_it: bool = True, cfg: Config | None = None
) -> tuple[Lesson, dict]:
    from instep.learner.measure import measure_clip
    from instep.teacher.calibrate import calibrate
    from instep.teacher.draft import draft_lesson

    cfg = cfg or Config.from_env()
    video = video.resolve()
    info = probe(video)
    transcriber = registry.transcriber(cfg)
    transcript = transcribe_if_spoken(video, cfg)
    outcome = draft_lesson(
        video,
        info,
        recording_ref(video),
        transcript,
        registry.understander(cfg),
        settings,
        transcriber_name=f"{transcriber.name}:{cfg.whisper_model}",
    )
    lesson = outcome.lesson
    out = RUNS / "lessons" / video.stem / settings.label
    out.mkdir(parents=True, exist_ok=True)
    save_lesson(lesson, out / "lesson_draft.json")
    report: dict = {
        "video": video.name,
        "variant": settings.label,
        "model": outcome.model,
        "usage": outcome.usage,
        "draft_issues": outcome.issues,
        "transcript_language": transcript.language if transcript else None,
        "n_steps": len(lesson.steps),
    }
    if calibrate_it:
        segmenter = registry.segmenter(cfg)
        measures = measure_clip(
            video,
            lesson,
            segmenter,
            read_frames(video, TUTORIAL_FPS, SEG_WIDTH),
            TUTORIAL_FPS,
            SEG_WIDTH,
            progress=True,
        )
        lesson, cal = calibrate(lesson, measures)
        report["calibration"] = asdict(cal)
    save_lesson(lesson, out / "lesson.json")
    (out / "report.json").write_text(json.dumps(report, indent=2))
    return lesson, report


def tutorial_path(lesson: Lesson) -> Path | None:
    rec = lesson.provenance.recording
    if rec is None:
        return None
    p = Path(rec.path)
    return p if p.is_absolute() else ROOT / p


def learn(clip: Path, lesson_path: Path, use_judge: bool = True, cfg: Config | None = None):
    from instep.learner.machine import StepMachine
    from instep.learner.measure import measure_clip

    cfg = cfg or Config.from_env()
    clip = clip.resolve()
    lesson = load_lesson(lesson_path)
    measures = measure_clip(
        clip,
        lesson,
        registry.segmenter(cfg),
        read_frames(clip, LEARNER_FPS, SEG_WIDTH),
        LEARNER_FPS,
        SEG_WIDTH,
        progress=True,
    )
    tutorial = tutorial_path(lesson)

    def still_at(t: float) -> bytes:
        return to_jpeg(frame_at(clip, t, 768), 80)

    def reference_for(step: Step) -> bytes | None:
        t = step.completion.reference_frame_s
        if tutorial is None or t is None or not tutorial.exists():
            return None
        return to_jpeg(frame_at(tutorial, t, 768), 80)

    machine = StepMachine(
        lesson,
        judge=registry.judge(cfg) if use_judge else None,
        still_at=still_at,
        reference_for=reference_for,
    )
    for m in measures.frames:
        machine.feed(m)
    out = RUNS / "learn" / clip.stem / lesson.id
    out.mkdir(parents=True, exist_ok=True)
    (out / "events.json").write_text(json.dumps([e.model_dump() for e in machine.events], indent=2))
    return machine.events, measures, machine


PREP_EVERY_S = 2.0


def prepare(video: Path, cfg: Config | None = None) -> Path:
    """Write what a drafter needs (transcript, cuts, timestamped frame grids) to runs/prep."""
    from instep.media.frames import scene_cuts
    from instep.media.grid import video_grids

    cfg = cfg or Config.from_env()
    video = video.resolve()
    info = probe(video)
    out = RUNS / "prep" / video.stem
    out.mkdir(parents=True, exist_ok=True)
    transcript = transcribe_if_spoken(video, cfg)
    lines = [
        f"duration_s: {info.duration_s:.1f}",
        f"language: {transcript.language if transcript else 'none'}",
    ]
    lines += [
        f"[{s.start_s:.1f}-{s.end_s:.1f}] {s.text}"
        for s in (transcript.segments if transcript else [])
    ]
    (out / "transcript.txt").write_text("\n".join(lines) + "\n")
    (out / "cuts.txt").write_text(", ".join(f"{c:.1f}" for c in scene_cuts(video)) + "\n")
    video_grids(video, out / "grids", every_s=PREP_EVERY_S, per_page=24, cols=6)
    return out


def ingest(video: Path, draft_path: Path, by: str, calibrate_it: bool, cfg: Config | None = None):
    """A draft written outside the API (e.g. by a Claude Code subagent from the prep folder)."""
    from datetime import UTC, datetime

    from instep import __version__
    from instep.learner.measure import measure_clip
    from instep.lesson.schema import MadeBy
    from instep.providers.base import DraftLesson
    from instep.teacher.calibrate import calibrate
    from instep.teacher.draft import to_lesson

    cfg = cfg or Config.from_env()
    video = video.resolve()
    info = probe(video)
    transcript = transcribe_if_spoken(video, cfg)
    draft = DraftLesson.model_validate_json(draft_path.read_text())
    n = int(info.duration_s // PREP_EVERY_S) + 1
    lesson, issues = to_lesson(
        draft,
        recording=recording_ref(video),
        transcript=transcript,
        made_by=MadeBy(
            understanding=by,
            segmenter="none",
            transcriber=f"whisper-mlx:{cfg.whisper_model}",
            pipeline_version=__version__,
            created_at=datetime.now(UTC),
        ),
        frame_times=[i * PREP_EVERY_S for i in range(n)],
    )
    report: dict = {
        "video": video.name,
        "variant": by,
        "draft_issues": issues,
        "n_steps": len(lesson.steps),
    }
    out = RUNS / "lessons" / video.stem / by.replace(":", "-")
    out.mkdir(parents=True, exist_ok=True)
    save_lesson(lesson, out / "lesson_draft.json")
    if calibrate_it:
        measures = measure_clip(
            video,
            lesson,
            registry.segmenter(cfg),
            read_frames(video, TUTORIAL_FPS, SEG_WIDTH),
            TUTORIAL_FPS,
            SEG_WIDTH,
            progress=True,
        )
        lesson, cal = calibrate(lesson, measures)
        report["calibration"] = asdict(cal)
    save_lesson(lesson, out / "lesson.json")
    (out / "report.json").write_text(json.dumps(report, indent=2))
    return lesson, report


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="instep")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("lesson")
    a.add_argument("video", type=Path)
    a.add_argument("--variant", default="draft_v1:2:120:512:tx")
    a.add_argument("--no-calibrate", action="store_true")
    a.add_argument("--publish", action="store_true", help="copy to data/lessons/generated/")
    b = sub.add_parser("learn")
    b.add_argument("clip", type=Path)
    b.add_argument("lesson", type=Path)
    b.add_argument("--no-judge", action="store_true")
    g = sub.add_parser("grid")
    g.add_argument("video", type=Path)
    g.add_argument("--every", type=float, default=1.0)
    pr = sub.add_parser("prepare")
    pr.add_argument("video", type=Path)
    ing = sub.add_parser("ingest")
    ing.add_argument("video", type=Path)
    ing.add_argument("draft", type=Path)
    ing.add_argument("--by", default="claude-code-subagent:draft_v1")
    ing.add_argument("--no-calibrate", action="store_true")
    ing.add_argument("--publish", action="store_true")
    args = ap.parse_args(argv)

    if args.cmd == "lesson":
        lesson, report = build_lesson(
            args.video, parse_variant(args.variant), not args.no_calibrate
        )
        if args.publish:
            save_lesson(lesson, LESSONS / f"{lesson.id}.json")
        print(json.dumps({k: v for k, v in report.items() if k != "usage"}, indent=2))
    elif args.cmd == "learn":
        events, _, machine = learn(args.clip, args.lesson, not args.no_judge)
        for e in events:
            print(f"{e.t_s:7.1f}s  {e.kind:8s} {e.step_id or '':24s} {e.cue or ''}")
        print(f"judge calls: {machine.judge_calls}")
    elif args.cmd == "grid":
        from instep.media.grid import video_grids

        pages = video_grids(args.video, RUNS / "grids" / args.video.stem, every_s=args.every)
        print("\n".join(str(p) for p in pages))
    elif args.cmd == "prepare":
        print(prepare(args.video))
    elif args.cmd == "ingest":
        lesson, report = ingest(args.video, args.draft, args.by, not args.no_calibrate)
        if args.publish:
            save_lesson(lesson, LESSONS / f"{lesson.id}.json")
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
