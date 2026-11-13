"""Where learner frames come from. FileReplay today; the Mock Device Kit stream later."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import numpy as np

from instep.media.frames import frame_at, read_frames


@dataclass(frozen=True)
class Frame:
    t_s: float  # seconds since the attempt started
    image: np.ndarray  # H x W x 3, RGB, uint8


class FrameSource(Protocol):
    def frames(self) -> Iterator[Frame]: ...

    def still(self, t_s: float) -> np.ndarray:
        """A sharper single frame at ``t_s`` for the judge (a photo capture on the glasses)."""
        ...


@dataclass(frozen=True)
class FileReplay:
    """A recorded attempt played back as if it were arriving from the glasses."""

    path: Path
    fps: float
    width: int
    still_width: int = 768

    def frames(self) -> Iterator[Frame]:
        for t, image in read_frames(self.path, self.fps, self.width):
            yield Frame(t, image)

    def still(self, t_s: float) -> np.ndarray:
        return frame_at(self.path, t_s, self.still_width)
