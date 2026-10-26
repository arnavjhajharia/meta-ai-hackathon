"""Fast path: what the segmenter sees in each frame, reduced to a few numbers per object.

The step machine never looks at pixels; it reads these measurements. They are cached per clip,
so tuning the step logic never re-runs the segmenter.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from pydantic import BaseModel

from instep import cache
from instep.lesson.schema import Lesson
from instep.providers.base import Detection, Segmenter

HAND_PROMPT = "hand"
REGION_PAD = 0.15  # grow the work area box by this fraction on each side


class ObjectSeen(BaseModel):
    score: float  # best detection score, 0 if not found
    in_work_area: bool  # centre or most of its mask inside the work area region
    coverage: float  # share of the work area region its mask covers


class FrameMeasure(BaseModel):
    t_s: float
    work_area_visible: bool
    work_area_box: tuple[float, float, float, float] | None  # normalised 0..1
    objects: dict[str, ObjectSeen]  # by object id
    hands_in_work_area: bool
    motion: float  # mean abs change in the work area since the previous frame, 0..1


class ClipMeasures(BaseModel):
    clip: str
    fps: float
    width: int
    segmenter: str
    frames: list[FrameMeasure]


@dataclass
class Measurer:
    lesson: Lesson
    segmenter: Segmenter
    min_score: float = 0.30
    _prev: np.ndarray | None = field(default=None, repr=False)

    def prompts(self) -> list[str]:
        ps = [o.prompt for o in self.lesson.objects]
        return ps + ([HAND_PROMPT] if HAND_PROMPT not in ps else [])

    def measure(self, t_s: float, image: np.ndarray) -> FrameMeasure:
        h, w = image.shape[:2]
        dets = [
            d for d in self.segmenter.segment(image, self.prompts()) if d.score >= self.min_score
        ]
        by_prompt: dict[str, list[Detection]] = {}
        for d in dets:
            by_prompt.setdefault(d.prompt, []).append(d)

        wa = self.lesson.object(self.lesson.work_area_object)
        wa_dets = sorted(by_prompt.get(wa.prompt, []), key=lambda d: -d.score)
        region = _pad(wa_dets[0].box, w, h) if wa_dets else None

        objects: dict[str, ObjectSeen] = {}
        for o in self.lesson.objects:
            mine = by_prompt.get(o.prompt, [])
            if o.id == wa.id:
                objects[o.id] = ObjectSeen(
                    score=wa_dets[0].score if wa_dets else 0.0,
                    in_work_area=bool(wa_dets),
                    coverage=1.0,
                )
                continue
            objects[o.id] = _seen(mine, region, w, h)

        hands = _seen(by_prompt.get(HAND_PROMPT, []), region, w, h)
        motion = self._motion(image, region)
        return FrameMeasure(
            t_s=round(t_s, 3),
            work_area_visible=region is not None,
            work_area_box=(region[0] / w, region[1] / h, region[2] / w, region[3] / h)
            if region
            else None,
            objects=objects,
            hands_in_work_area=hands.in_work_area,
            motion=motion,
        )

    def _motion(self, image: np.ndarray, region: tuple | None) -> float:
        small = image[::8, ::8].mean(axis=-1).astype(np.float32) / 255.0
        prev, self._prev = self._prev, small
        if prev is None or prev.shape != small.shape:
            return 0.0
        diff = np.abs(small - prev)
        if region is not None:
            x0, y0, x1, y1 = (int(v / 8) for v in region)
            crop = diff[y0 : max(y1, y0 + 1), x0 : max(x1, x0 + 1)]
            if crop.size:
                diff = crop
        return round(float(diff.mean()), 4)


def _pad(box: tuple, w: int, h: int) -> tuple[float, float, float, float]:
    x0, y0, x1, y1 = box
    px, py = (x1 - x0) * REGION_PAD, (y1 - y0) * REGION_PAD
    return (max(0.0, x0 - px), max(0.0, y0 - py), min(float(w), x1 + px), min(float(h), y1 + py))


def _seen(dets: list[Detection], region: tuple | None, w: int, h: int) -> ObjectSeen:
    if not dets:
        return ObjectSeen(score=0.0, in_work_area=False, coverage=0.0)
    best = max(d.score for d in dets)
    if region is None:
        return ObjectSeen(score=best, in_work_area=False, coverage=0.0)
    x0, y0, x1, y1 = (int(v) for v in region)
    area = max(1, (x1 - x0) * (y1 - y0))
    inside, covered = False, 0
    for d in dets:
        cx, cy = (d.box[0] + d.box[2]) / 2, (d.box[1] + d.box[3]) / 2
        centre_in = x0 <= cx <= x1 and y0 <= cy <= y1
        if d.mask is not None:
            sub = d.mask[y0:y1, x0:x1]
            n_in = int(sub.sum())
            n_all = int(d.mask.sum()) or 1
            covered += n_in
            inside |= centre_in or n_in / n_all > 0.5
        else:
            bx0, by0 = max(x0, d.box[0]), max(y0, d.box[1])
            bx1, by1 = min(x1, d.box[2]), min(y1, d.box[3])
            covered += int(max(0, bx1 - bx0) * max(0, by1 - by0))
            inside |= centre_in
    return ObjectSeen(score=best, in_work_area=inside, coverage=round(min(1.0, covered / area), 4))


def measure_clip(
    clip: Path,
    lesson: Lesson,
    segmenter: Segmenter,
    frames: Iterable[tuple[float, np.ndarray]],
    fps: float,
    width: int,
    progress: bool = False,
) -> ClipMeasures:
    """Measure every sampled frame of a clip, cached by clip content, prompts and segmenter."""
    m = Measurer(lesson, segmenter)
    k = cache.key(
        clip=cache.file_sha256(clip),
        prompts=m.prompts(),
        ids=[o.id for o in lesson.objects],
        work_area=lesson.work_area_object,
        segmenter=segmenter.name,
        fps=fps,
        width=width,
        v=2,
    )

    def run() -> dict:
        out = []
        for i, (t, img) in enumerate(frames):
            out.append(m.measure(t, img))
            if progress and i % 20 == 0:
                print(f"  {clip.name}: {t:.0f}s", flush=True)
        return ClipMeasures(
            clip=clip.name, fps=fps, width=width, segmenter=segmenter.name, frames=out
        ).model_dump()

    return ClipMeasures.model_validate(cache.cached_json("measure", k, run))
