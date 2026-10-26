"""Frame grid with segmentation masks painted on: does the segmenter see what the lesson names?

python -m instep.viz.overlay <video> <lesson.json> [--n 12] [--times 10 20 ...]
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from instep.config import ROOT, Config
from instep.lesson.io import load_lesson
from instep.lesson.schema import Lesson
from instep.media.frames import frame_at, probe
from instep.media.grid import grid_image
from instep.providers import registry
from instep.providers.base import Segmenter

PALETTE = [
    (31, 119, 180), (255, 127, 14), (44, 160, 44), (214, 39, 40), (148, 103, 189),
    (140, 86, 75), (227, 119, 194), (127, 127, 127), (188, 189, 34), (23, 190, 207),
]  # fmt: skip


def paint(image: np.ndarray, lesson: Lesson, segmenter: Segmenter) -> tuple[np.ndarray, list[str]]:
    prompts = [o.prompt for o in lesson.objects] + ["hand"]
    colour = {o.prompt: PALETTE[i % len(PALETTE)] for i, o in enumerate(lesson.objects)}
    colour.setdefault("hand", (255, 255, 255))
    out = image.astype(np.float32).copy()
    found = []
    for d in sorted(segmenter.segment(image, prompts), key=lambda d: d.score):
        c = np.array(colour.get(d.prompt, (255, 255, 0)), dtype=np.float32)
        if d.mask is not None:
            out[d.mask] = out[d.mask] * 0.45 + c * 0.55
        x0, y0, x1, y1 = (int(v) for v in d.box)
        out[y0 : y0 + 2, x0:x1] = c
        out[max(0, y1 - 2) : y1, x0:x1] = c
        out[y0:y1, x0 : x0 + 2] = c
        out[y0:y1, max(0, x1 - 2) : x1] = c
        found.append(f"{d.prompt} {d.score:.2f}")
    return out.clip(0, 255).astype(np.uint8), found


def render(video: Path, lesson: Lesson, out: Path, times: list[float], cfg: Config) -> Path:
    seg = registry.segmenter(cfg)
    tiles = []
    for t in times:
        img, found = paint(frame_at(video, t, 640), lesson, seg)
        tiles.append((img, f"{t:.1f}s\n" + "\n".join(found[-5:])))
    out.parent.mkdir(parents=True, exist_ok=True)
    grid_image(tiles, cols=4, tile_width=400).save(out, quality=85)
    return out


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("video", type=Path)
    ap.add_argument("lesson", type=Path)
    ap.add_argument("--n", type=int, default=12)
    ap.add_argument("--times", type=float, nargs="*")
    args = ap.parse_args(argv)
    lesson = load_lesson(args.lesson)
    dur = probe(args.video).duration_s
    times = args.times or list(np.linspace(dur * 0.05, dur * 0.95, args.n).round(1))
    out = ROOT / "runs" / "overlay" / f"{args.video.stem}__{lesson.id}.jpg"
    print(render(args.video, lesson, out, times, Config.from_env()))


if __name__ == "__main__":
    main()
