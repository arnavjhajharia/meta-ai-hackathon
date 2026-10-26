"""Claude via the Anthropic API (stand-in for Muse Spark). Every call is cached and logged."""

from __future__ import annotations

import base64
import json
import time
from dataclasses import dataclass
from pathlib import Path

from instep import cache
from instep.providers.base import (
    DraftLesson,
    DraftRequest,
    DraftResult,
    StillVerdict,
)

# USD per million tokens (input, output, cache read), Anthropic first-party, Oct 2026.
PRICES = {
    "claude-opus-5-5": (4.0, 20.0, 0.20),
    "claude-sonnet-5-5": (2.0, 10.0, 0.20),
    "claude-haiku-5-5": (0.10, 0.50, 0.01),
}
SPEND_LOG = cache.ROOT / "spend.jsonl"
FALLBACK_BETA = "server-side-fallback-2026-07-01"


class SpendCapReached(RuntimeError):
    pass


def spent_usd(log: Path = SPEND_LOG) -> float:
    if not log.exists():
        return 0.0
    return sum(json.loads(line)["usd"] for line in log.read_text().splitlines() if line)


def _cost(model: str, usage: dict[str, int]) -> float:
    pin, pout, pread = PRICES.get(model, PRICES["claude-opus-5-5"])
    return (
        usage.get("input_tokens", 0) * pin
        + usage.get("cache_creation_input_tokens", 0) * pin * 1.25
        + usage.get("cache_read_input_tokens", 0) * pread
        + usage.get("output_tokens", 0) * pout
    ) / 1e6


def _usage(response) -> dict[str, int]:
    u = response.usage
    return {
        k: int(getattr(u, k, 0) or 0)
        for k in (
            "input_tokens",
            "output_tokens",
            "cache_creation_input_tokens",
            "cache_read_input_tokens",
        )
    }


def _image(jpeg: bytes) -> dict:
    data = base64.standard_b64encode(jpeg).decode()
    return {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": data}}


class _Client:
    def __init__(self, spend_cap_usd: float, purpose: str):
        import anthropic

        from instep.config import load_env

        load_env()
        self.client = anthropic.Anthropic(max_retries=4)
        self.cap = spend_cap_usd
        self.purpose = purpose

    def parse(self, model: str, effort: str, output_format, system: str, content: list) -> tuple:
        if spent_usd() >= self.cap:
            raise SpendCapReached(f"spent ${spent_usd():.2f} of the ${self.cap:.2f} cap")
        start = time.time()
        response = self.client.beta.messages.parse(
            model=model,
            max_tokens=32000,
            betas=[FALLBACK_BETA],
            fallbacks="default",
            output_config={"effort": effort},
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": content}],
            output_format=output_format,
        )
        usage = _usage(response)
        record = {
            "t": time.time(),
            "purpose": self.purpose,
            "model": response.model,
            "usd": round(_cost(response.model, usage), 5),
            "seconds": round(time.time() - start, 1),
            **usage,
        }
        SPEND_LOG.parent.mkdir(parents=True, exist_ok=True)
        with SPEND_LOG.open("a") as f:
            f.write(json.dumps(record) + "\n")
        if response.stop_reason == "refusal":
            raise RuntimeError(f"model refused: {response.stop_details}")
        if response.parsed_output is None:
            raise RuntimeError(f"no parsed output (stop_reason={response.stop_reason})")
        return response.parsed_output, response.model, usage


def _transcript_text(request: DraftRequest) -> str:
    if request.transcript is None or not request.transcript.segments:
        return "(no speech in this recording)"
    lines = [f"[{s.start_s:.1f}-{s.end_s:.1f}] {s.text}" for s in request.transcript.segments]
    return f"language: {request.transcript.language}\n" + "\n".join(lines)


@dataclass
class ClaudeUnderstander:
    model: str = "claude-opus-5-5"
    effort: str = "high"
    spend_cap_usd: float = 15.0
    name: str = "claude"

    def draft_lesson(self, request: DraftRequest) -> DraftResult:
        content: list = [
            {
                "type": "text",
                "text": (
                    f"Recording length: {request.duration_s:.1f} s.\n"
                    f"Shot cuts at: {', '.join(f'{c:.1f}' for c in request.cuts) or 'none'}.\n"
                    + "".join(f"{k}: {v}\n" for k, v in sorted(request.hints.items()))
                    + f"\nTranscript (seconds):\n{_transcript_text(request)}\n\n"
                    f"Frames follow, each labelled with its time in seconds."
                ),
            }
        ]
        for frame in request.frames:
            content.append({"type": "text", "text": f"t={frame.t_s:.1f}s"})
            content.append(_image(frame.jpeg))
        content.append({"type": "text", "text": "Write the lesson now."})

        k = cache.key(
            provider=self.name,
            model=self.model,
            effort=self.effort,
            system=request.instructions,
            content=json.dumps(content, sort_keys=True).encode(),
        )

        def call() -> dict:
            client = _Client(self.spend_cap_usd, f"draft:{request.prompt_version}")
            draft, model, usage = client.parse(
                self.model, self.effort, DraftLesson, request.instructions, content
            )
            return {"draft": draft.model_dump(), "model": model, "usage": usage}

        data = cache.cached_json("draft", k, call)
        return DraftResult(
            draft=DraftLesson.model_validate(data["draft"]),
            model=data["model"],
            usage=data["usage"],
        )


JUDGE_SYSTEM = """You check whether a learner has finished one step of a hands-on task.

You get the learner's current view (first person, from a camera on their chest or head) and,
when available, a frame from the teacher's tutorial showing that step finished. The two cameras
see the work from different angles, distances and lighting; judge the state of the work, not the
picture. Only say done when the described end state is clearly visible in the learner's view.
If the work area is blocked, blurred, out of frame or too dark to judge, set visible to false
and done to false. Never guess done from context. Keep "missing" to one short plain sentence."""


@dataclass
class ClaudeStillJudge:
    model: str = "claude-sonnet-5-5"
    effort: str = "low"
    spend_cap_usd: float = 15.0
    name: str = "claude-judge"

    def judge(
        self, learner_jpeg: bytes, reference_jpeg: bytes | None, end_state: str, step_title: str
    ) -> StillVerdict:
        content: list = [
            {"type": "text", "text": f"Step: {step_title}\nDone looks like: {end_state}"}
        ]
        if reference_jpeg:
            content += [{"type": "text", "text": "Teacher, step finished:"}, _image(reference_jpeg)]
        content += [{"type": "text", "text": "Learner now:"}, _image(learner_jpeg)]
        k = cache.key(
            provider=self.name,
            model=self.model,
            effort=self.effort,
            system=JUDGE_SYSTEM,
            learner=learner_jpeg,
            reference=reference_jpeg or b"",
            end_state=end_state,
            step=step_title,
        )

        def call() -> dict:
            client = _Client(self.spend_cap_usd, "judge")
            verdict, _, _ = client.parse(
                self.model, self.effort, StillVerdict, JUDGE_SYSTEM, content
            )
            return verdict.model_dump()

        return StillVerdict.model_validate(cache.cached_json("judge", k, call))
