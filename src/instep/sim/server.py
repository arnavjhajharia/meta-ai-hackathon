"""Web glasses simulator.

The page plays a learner recording and reports its clock over a websocket. The server feeds the
step machine every cached measurement up to that time and sends back the events, so pausing and
seeking work (a seek backwards replays from the start). A live glasses stream (Mock Device Kit)
would replace the cached measurements with frames measured as they arrive.

  .venv/bin/python -m instep.sim.server   ->  http://127.0.0.1:8765
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from instep.config import ROOT, Config
from instep.eval.labels import load_labels
from instep.learner.machine import StepMachine
from instep.learner.measure import measure_clip
from instep.lesson.io import load_lesson
from instep.lesson.schema import Lesson, Step
from instep.media.frames import frame_at, read_frames, to_jpeg
from instep.providers import registry

STATIC = Path(__file__).parent / "static"
RECORDINGS = ROOT / "data" / "recordings"
LESSON_DIRS = [ROOT / "data" / "lessons" / "generated", ROOT / "data" / "lessons" / "hand"]
LEARNER_FPS = 2.0
SEG_WIDTH = 640

app = FastAPI()
app.mount("/static", StaticFiles(directory=STATIC), name="static")


def lessons() -> dict[str, Path]:
    out = {}
    for d in LESSON_DIRS:
        for p in sorted(d.glob("*.json")):
            out[p.stem] = p
    return out


def lesson_by_id(lesson_id: str) -> Lesson:
    path = lessons().get(lesson_id)
    if path is None:
        raise HTTPException(404, f"no lesson {lesson_id}")
    return load_lesson(path)


def clip_path(name: str) -> Path:
    p = (RECORDINGS / name).resolve()
    if p.parent != RECORDINGS.resolve() or not p.exists():
        raise HTTPException(404, f"no recording {name}")
    return p


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.get("/api/catalog")
def catalog() -> JSONResponse:
    ls = {}
    for lid, path in lessons().items():
        lesson = load_lesson(path)
        ls[lid] = {"title": lesson.title, "task": lesson.task, "steps": len(lesson.steps)}
    clips = [p.name for p in sorted(RECORDINGS.glob("learner_*.mp4"))]
    return JSONResponse({"lessons": ls, "clips": clips})


@app.get("/api/lesson/{lesson_id}")
def lesson_json(lesson_id: str) -> JSONResponse:
    lesson = lesson_by_id(lesson_id)
    tutorial = lesson.provenance.recording.path if lesson.provenance.recording else None
    return JSONResponse(
        {
            "lesson": lesson.model_dump(mode="json"),
            "tutorial": Path(tutorial).name if tutorial else None,
            "claims": sorted(lesson.claims()),
        }
    )


@app.get("/api/labels/{clip}")
def labels(clip: str) -> JSONResponse:
    path = ROOT / "data" / "labels" / f"{Path(clip).stem}.json"
    if not path.exists():
        return JSONResponse({"rows": []})
    return JSONResponse(load_labels(path).model_dump(mode="json"))


@app.get("/media/{name}")
def media(name: str) -> FileResponse:
    return FileResponse(clip_path(name), media_type="video/mp4")


class Session:
    def __init__(self, clip: Path, lesson: Lesson, use_judge: bool):
        cfg = Config.from_env()
        self.clip, self.lesson = clip, lesson
        self.frames = measure_clip(
            clip,
            lesson,
            registry.segmenter(cfg),
            read_frames(clip, LEARNER_FPS, SEG_WIDTH),
            LEARNER_FPS,
            SEG_WIDTH,
        ).frames
        self.judge = registry.judge(cfg) if use_judge else None
        rec = lesson.provenance.recording
        self.tutorial = ROOT / rec.path if rec and not Path(rec.path).is_absolute() else None
        self.reset()

    def reset(self) -> None:
        self.machine = StepMachine(
            self.lesson,
            judge=self.judge,
            still_at=lambda t: to_jpeg(frame_at(self.clip, t, 768), 80),
            reference_for=self._reference,
        )
        self.i = 0
        self.t = 0.0

    def _reference(self, step: Step) -> bytes | None:
        t = step.completion.reference_frame_s
        if self.tutorial is None or t is None or not self.tutorial.exists():
            return None
        return to_jpeg(frame_at(self.tutorial, t, 768), 80)

    def advance_to(self, t: float) -> tuple[list, list]:
        if t + 0.25 < self.t:
            self.reset()
        self.t = t
        events, measures = [], []
        while self.i < len(self.frames) and self.frames[self.i].t_s <= t:
            m = self.frames[self.i]
            events += self.machine.feed(m)
            measures.append(
                {
                    "t": m.t_s,
                    "visible": m.work_area_visible,
                    "box": m.work_area_box,
                    "hands": m.hands_in_work_area,
                    "seen": [k for k, v in m.objects.items() if v.in_work_area and v.score >= 0.35],
                }
            )
            self.i += 1
        return events, measures


@app.websocket("/ws")
async def ws(socket: WebSocket) -> None:
    await socket.accept()
    session: Session | None = None
    try:
        while True:
            msg = json.loads(await socket.receive_text())
            if msg["type"] == "open":
                await socket.send_text(json.dumps({"type": "status", "text": "Measuring clip"}))
                session = await asyncio.to_thread(
                    Session,
                    clip_path(msg["clip"]),
                    lesson_by_id(msg["lesson"]),
                    bool(msg.get("judge", True)),
                )
                await socket.send_text(
                    json.dumps(
                        {
                            "type": "ready",
                            "duration": session.frames[-1].t_s if session.frames else 0,
                        }
                    )
                )
            elif msg["type"] == "clock" and session is not None:
                events, measures = await asyncio.to_thread(session.advance_to, float(msg["t"]))
                await socket.send_text(
                    json.dumps(
                        {
                            "type": "tick",
                            "t": msg["t"],
                            "step": session.machine.k,
                            "frozen": session.machine.frozen,
                            "last": measures[-1] if measures else None,
                            "events": [e.model_dump(mode="json") for e in events],
                        }
                    )
                )
    except WebSocketDisconnect:
        return


def main() -> None:
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="warning")


if __name__ == "__main__":
    main()
