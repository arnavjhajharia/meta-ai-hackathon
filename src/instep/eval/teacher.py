"""Scoring tutorial -> Lesson.

Two kinds of score:
- automatic checks that need no labels (grounding, findability, repairs, consistency between
  prompt variants). Good for comparing prompts; not proof of correctness.
- agreement with a human-confirmed step list (data/labels/tutorials/<video stem>.json). This is
  the real score; it only exists once a human has confirmed the reference.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

from instep.lesson.schema import Contract, Lesson, Span

VAGUE = {"ingredients", "mixture", "toppings", "stuff", "things", "items", "food", "materials"}


class RefStep(Contract):
    title: str
    start_s: float
    end_s: float


class StepReference(Contract):
    video: str
    confirmed_by: str = Field(min_length=1)
    steps: list[RefStep]


def load_reference(path: Path) -> StepReference:
    return StepReference.model_validate(json.loads(path.read_text()))


def iou(a: Span | RefStep, b: Span | RefStep) -> float:
    inter = max(0.0, min(a.end_s, b.end_s) - max(a.start_s, b.start_s))
    union = max(a.end_s, b.end_s) - min(a.start_s, b.start_s)
    return inter / union if union > 0 else 0.0


def match(pred: list, ref: list, min_overlap: float = 0.2) -> list[tuple[int, int, float]]:
    """Greedy one-to-one matching by temporal overlap, in order."""
    pairs = sorted(
        ((iou(p, r), i, j) for i, p in enumerate(pred) for j, r in enumerate(ref)), reverse=True
    )
    used_p, used_r, out = set(), set(), []
    for score, i, j in pairs:
        if score < min_overlap or i in used_p or j in used_r:
            continue
        used_p.add(i)
        used_r.add(j)
        out.append((i, j, score))
    return sorted(out)


class AutoScore(BaseModel):
    n_steps: int
    repairs: int
    tips_kept: int
    tips_dropped: int
    vague_prompts: int
    findability_mean: float | None
    unfindable_objects: int
    end_state_steps: int
    out_of_view_share: float | None


def auto_score(lesson: Lesson, report: dict) -> AutoScore:
    issues = report.get("draft_issues", [])
    dropped = sum("dropped" in i or "not in transcript" in i for i in issues)
    cal = report.get("calibration") or {}
    find = cal.get("findability") or {}
    return AutoScore(
        n_steps=len(lesson.steps),
        repairs=len(issues) - dropped,
        tips_kept=sum(len(s.tips) for s in lesson.steps),
        tips_dropped=dropped,
        vague_prompts=sum(
            any(w in VAGUE for w in o.prompt.lower().split()) for o in lesson.objects
        ),
        findability_mean=round(sum(find.values()) / len(find), 3) if find else None,
        unfindable_objects=sum(v < 0.05 for v in find.values()),
        end_state_steps=sum(s.completion.kind == "end_state" for s in lesson.steps),
        out_of_view_share=cal.get("out_of_view_share"),
    )


class RefScore(BaseModel):
    recall: float
    precision: float
    start_err_s: float | None  # median absolute error over matched steps
    end_err_s: float | None
    within_3s: float  # share of matched boundaries within 3 s


def ref_score(lesson: Lesson, ref: StepReference) -> RefScore:
    pred = [s.best_span for s in lesson.steps]
    pairs = match(pred, ref.steps)
    errs_s = sorted(abs(pred[i].start_s - ref.steps[j].start_s) for i, j, _ in pairs)
    errs_e = sorted(abs(pred[i].end_s - ref.steps[j].end_s) for i, j, _ in pairs)
    both = errs_s + errs_e
    return RefScore(
        recall=round(len(pairs) / max(1, len(ref.steps)), 3),
        precision=round(len(pairs) / max(1, len(pred)), 3),
        start_err_s=errs_s[len(errs_s) // 2] if errs_s else None,
        end_err_s=errs_e[len(errs_e) // 2] if errs_e else None,
        within_3s=round(sum(e <= 3 for e in both) / max(1, len(both)), 3),
    )


def consistency(a: Lesson, b: Lesson) -> float:
    """Agreement between two lessons of the same video (e.g. two prompt variants): matched
    steps over the larger step count. 1.0 means same steps at the same times."""
    pa, pb = [s.best_span for s in a.steps], [s.best_span for s in b.steps]
    pairs = match(pa, pb, 0.3)
    return round(sum(score for _, _, score in pairs) / max(len(pa), len(pb), 1), 3)
