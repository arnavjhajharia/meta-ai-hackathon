"""Deterministic fakes for tests: no network, no GPU, no money."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from instep.providers.base import (
    Detection,
    DraftLesson,
    DraftRequest,
    DraftResult,
    StillVerdict,
    Transcript,
)


@dataclass
class FakeTranscriber:
    transcript: Transcript
    name: str = "fake"

    def transcribe(self, media_path: Path) -> Transcript:
        return self.transcript


@dataclass
class FakeUnderstander:
    draft: DraftLesson
    name: str = "fake"
    calls: list[DraftRequest] = field(default_factory=list)

    def draft_lesson(self, request: DraftRequest) -> DraftResult:
        self.calls.append(request)
        return DraftResult(draft=self.draft, model="fake", usage={})


@dataclass
class ColourSegmenter:
    """Finds each prompt by a fixed RGB colour (for synthetic frames only)."""

    colours: dict[str, tuple[int, int, int]]
    tolerance: int = 30
    name: str = "fake-colour"

    def segment(self, image: np.ndarray, prompts: list[str]) -> list[Detection]:
        out = []
        for p in prompts:
            if p not in self.colours:
                continue
            target = np.array(self.colours[p], dtype=np.int16)
            mask = np.all(np.abs(image.astype(np.int16) - target) <= self.tolerance, axis=-1)
            if mask.sum() < 20:
                continue
            ys, xs = np.nonzero(mask)
            box = (float(xs.min()), float(ys.min()), float(xs.max() + 1), float(ys.max() + 1))
            out.append(Detection(prompt=p, score=0.99, box=box, mask=mask))
        return out


@dataclass
class FakeStillJudge:
    decide: Callable[[bytes, str], bool]
    name: str = "fake"
    calls: int = 0

    def judge(
        self, learner_jpeg: bytes, reference_jpeg: bytes | None, end_state: str, step_title: str
    ) -> StillVerdict:
        self.calls += 1
        done = self.decide(learner_jpeg, end_state)
        return StillVerdict(done=done, confidence=0.9, visible=True, missing="" if done else "x")
