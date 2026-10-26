"""Timestamped frame grids: our eyes on a video (lesson-review, look, label)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from instep.media.frames import read_frames


def _font(size: int) -> ImageFont.ImageFont:
    for name in ("/System/Library/Fonts/Supplemental/Arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def grid_image(
    tiles: list[tuple[np.ndarray, str]], cols: int = 4, tile_width: int = 320
) -> Image.Image:
    """Lay out (image, caption) tiles in a grid, caption burned into the top-left corner."""
    if not tiles:
        raise ValueError("no tiles")
    h0, w0 = tiles[0][0].shape[:2]
    tile_h = int(h0 * tile_width / w0)
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tile_width, rows * tile_h), "black")
    draw = ImageDraw.Draw(sheet)
    font = _font(14)
    for i, (img, caption) in enumerate(tiles):
        x, y = (i % cols) * tile_width, (i // cols) * tile_h
        sheet.paste(Image.fromarray(img).resize((tile_width, tile_h)), (x, y))
        for j, line in enumerate(caption.split("\n")):
            ty = y + 4 + j * 17
            bbox = draw.textbbox((x + 4, ty), line, font=font)
            draw.rectangle(bbox, fill=(0, 0, 0))
            draw.text((x + 4, ty), line, fill=(255, 255, 0), font=font)
    return sheet


def video_grids(
    path: Path,
    out_dir: Path,
    every_s: float = 1.0,
    per_page: int = 24,
    cols: int = 6,
    captions: dict[float, str] | None = None,
) -> list[Path]:
    """Frames every ``every_s`` seconds, ``per_page`` per image. Returns the pages written."""
    out_dir.mkdir(parents=True, exist_ok=True)
    frames = list(read_frames(path, fps=1.0 / every_s, width=320))
    pages = []
    for p in range(0, len(frames), per_page):
        tiles = []
        for t, img in frames[p : p + per_page]:
            extra = (captions or {}).get(round(float(t), 1), "")
            tiles.append((img, f"{t:.1f}s {extra}".strip()))
        page = out_dir / f"grid_{p // per_page:02d}.jpg"
        grid_image(tiles, cols=cols, tile_width=240).save(page, quality=80)
        pages.append(page)
    return pages
