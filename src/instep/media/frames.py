"""Read video with ffmpeg: probe, sample frames, find shot cuts, encode stills."""

from __future__ import annotations

import io
import json
import re
import subprocess
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image


@dataclass(frozen=True)
class VideoInfo:
    duration_s: float
    fps: float
    width: int
    height: int
    has_audio: bool


def probe(path: Path) -> VideoInfo:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    data = json.loads(out)
    video = next(s for s in data["streams"] if s["codec_type"] == "video")
    num, den = video.get("avg_frame_rate", "30/1").split("/")
    fps = float(num) / float(den) if float(den) else 30.0
    return VideoInfo(
        duration_s=float(data["format"]["duration"]),
        fps=fps,
        width=int(video["width"]),
        height=int(video["height"]),
        has_audio=any(s["codec_type"] == "audio" for s in data["streams"]),
    )


def _scaled_size(info: VideoInfo, width: int) -> tuple[int, int]:
    height = int(round(info.height * width / info.width / 2) * 2)
    return width, height


def read_frames(path: Path, fps: float, width: int = 640) -> Iterator[tuple[float, np.ndarray]]:
    """Yield (t_s, RGB uint8 frame) sampled at ``fps``, scaled to ``width``."""
    info = probe(path)
    w, h = _scaled_size(info, width)
    proc = subprocess.Popen(
        [
            "ffmpeg", "-v", "error", "-i", str(path),
            "-vf", f"fps={fps},scale={w}:{h}",
            "-f", "rawvideo", "-pix_fmt", "rgb24", "-",
        ],
        stdout=subprocess.PIPE,
    )  # fmt: skip
    assert proc.stdout is not None
    size = w * h * 3
    i = 0
    try:
        while True:
            buf = proc.stdout.read(size)
            if len(buf) < size:
                break
            # the fps filter emits frame i at time i / fps (frames centred on that instant)
            yield i / fps, np.frombuffer(buf, np.uint8).reshape(h, w, 3)
            i += 1
    finally:
        proc.stdout.close()
        proc.wait()


def frame_at(path: Path, t_s: float, width: int = 640) -> np.ndarray:
    info = probe(path)
    w, h = _scaled_size(info, width)
    t = max(0.0, min(t_s, info.duration_s - 0.05))
    buf = subprocess.run(
        [
            "ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", str(path),
            "-frames:v", "1", "-vf", f"scale={w}:{h}",
            "-f", "rawvideo", "-pix_fmt", "rgb24", "-",
        ],
        check=True,
        capture_output=True,
    ).stdout  # fmt: skip
    return np.frombuffer(buf[: w * h * 3], np.uint8).reshape(h, w, 3)


def scene_cuts(path: Path, threshold: float = 0.3) -> list[float]:
    """Times of hard shot changes (edited tutorials cut a lot; a cut is never a step by itself)."""
    proc = subprocess.run(
        [
            "ffmpeg", "-v", "info", "-i", str(path),
            "-vf", f"scale=320:-2,select='gt(scene,{threshold})',showinfo",
            "-an", "-f", "null", "-",
        ],
        capture_output=True,
        text=True,
    )  # fmt: skip
    return [float(m) for m in re.findall(r"pts_time:([0-9.]+)", proc.stderr)]


def keyframe_times(
    duration_s: float, cuts: list[float], every_s: float, max_frames: int
) -> list[float]:
    """Uniform samples plus one frame just after each cut, thinned to ``max_frames``."""
    times = set(round(t, 1) for t in np.arange(every_s / 2, duration_s, every_s))
    times |= {round(min(c + 0.5, duration_s - 0.1), 1) for c in cuts}
    ordered = sorted(times)
    if len(ordered) > max_frames:
        idx = np.linspace(0, len(ordered) - 1, max_frames).round().astype(int)
        ordered = [ordered[i] for i in sorted(set(idx))]
    return ordered


def to_jpeg(image: np.ndarray, quality: int = 80) -> bytes:
    buf = io.BytesIO()
    Image.fromarray(image).save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


def from_jpeg(data: bytes) -> np.ndarray:
    return np.asarray(Image.open(io.BytesIO(data)).convert("RGB"))
