"""One interface per role. Swapping a stand-in for the Meta service is a config change."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Protocol

import numpy as np
from pydantic import BaseModel

# ---------- transcription (Whisper today, Muse Voice Transcribe later) ----------


class Word(BaseModel):
    start_s: float
    end_s: float
    text: str


class Segment(BaseModel):
    start_s: float
    end_s: float
    text: str
    words: list[Word] = []


class Transcript(BaseModel):
    language: str | None
    segments: list[Segment]


class Transcriber(Protocol):
    name: str

    def transcribe(self, media_path: Path) -> Transcript: ...


# ---------- understanding (Claude today, Muse Spark later) ----------
# The draft is deliberately plain (no constraints) so it maps onto any structured-output API.
# teacher/draft.py turns it into a validated Lesson.


class DraftObject(BaseModel):
    id: str
    prompt: str
    role: Literal["work_area", "ingredient", "material", "part", "tool", "container", "hand"]
    confusable_with: list[str]


class DraftTip(BaseModel):
    text: str
    quote: str | None
    quote_language: str | None
    source: Literal["speech", "caption", "action"]
    at_s: float


class DraftStep(BaseModel):
    id: str
    title: str
    instruction: str
    start_s: float
    end_s: float
    objects: list[str]
    completion_kind: Literal[
        "appears_in_work_area", "leaves_work_area", "coverage_change", "end_state", "manual"
    ]
    completion_object: str | None
    end_state: str
    reference_frame_s: float
    tips: list[DraftTip]
    optional: bool
    wait_s: float | None = None
    work_area: str | None = None  # object id, only when not the lesson's main work area


class DraftSpan(BaseModel):
    start_s: float
    end_s: float
    reason: str


class DraftLesson(BaseModel):
    title: str
    task: str
    language: str
    objects: list[DraftObject]
    work_area_object: str
    steps: list[DraftStep]
    not_part_of_task: list[DraftSpan]


@dataclass(frozen=True)
class TimedImage:
    t_s: float
    jpeg: bytes


@dataclass
class DraftRequest:
    frames: list[TimedImage]
    transcript: Transcript | None
    duration_s: float
    prompt_version: str
    instructions: str  # the versioned prompt text (teacher/prompts/<version>.md)
    cuts: list[float] = field(default_factory=list)
    hints: dict[str, str] = field(default_factory=dict)


@dataclass
class DraftResult:
    draft: DraftLesson
    model: str
    usage: dict[str, int]


class Understander(Protocol):
    name: str

    def draft_lesson(self, request: DraftRequest) -> DraftResult: ...


# ---------- segmentation (open stand-in / SAM 3 today, SAM 3.1 later) ----------


@dataclass
class Detection:
    prompt: str
    score: float
    box: tuple[float, float, float, float]  # x0, y0, x1, y1 in pixels of the input image
    mask: np.ndarray | None  # bool H x W, same size as the input image


class Segmenter(Protocol):
    name: str

    def segment(
        self, image: np.ndarray, prompts: list[str], solo: list[str] | None = None
    ) -> list[Detection]:
        """``solo``: prompts whose labels must be reliable (work areas, hands)."""
        ...


# ---------- still judgement (Claude today, Muse Spark later) ----------


class StillVerdict(BaseModel):
    done: bool
    confidence: float
    visible: bool  # can the work area be seen well enough to judge at all
    missing: str  # what is still missing, in plain words; empty when done


class StillJudge(Protocol):
    name: str

    def judge(
        self, learner_jpeg: bytes, reference_jpeg: bytes | None, end_state: str, step_title: str
    ) -> StillVerdict: ...
