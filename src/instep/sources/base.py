"""Where learner frames come from. FileReplay today; the Mock Device Kit stream later."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Protocol

import numpy as np


@dataclass(frozen=True)
class Frame:
    t_s: float  # seconds since the attempt started
    image: np.ndarray  # H x W x 3, RGB, uint8


class FrameSource(Protocol):
    def frames(self) -> Iterator[Frame]: ...
