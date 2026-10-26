"""Build the provider for each role from config. The only place that names vendors."""

from __future__ import annotations

from instep.config import Config
from instep.providers.base import Segmenter, StillJudge, Transcriber, Understander


def transcriber(cfg: Config) -> Transcriber:
    if cfg.transcriber == "whisper-mlx":
        from instep.providers.whisper_mlx import MlxWhisper

        return MlxWhisper(model=cfg.whisper_model)
    raise ValueError(f"unknown transcriber {cfg.transcriber!r}")


def understander(cfg: Config) -> Understander:
    if cfg.understander == "claude":
        from instep.providers.claude import ClaudeUnderstander

        return ClaudeUnderstander(
            model=cfg.draft_model, effort=cfg.draft_effort, spend_cap_usd=cfg.spend_cap_usd
        )
    raise ValueError(f"unknown understander {cfg.understander!r}")


def segmenter(cfg: Config) -> Segmenter:
    from instep.providers import segment_open

    if cfg.segmenter == "gdino-sam2":
        return segment_open.GdinoSam2()
    if cfg.segmenter == "gdino":
        return segment_open.GdinoSam2(with_masks=False, name="gdino")
    if cfg.segmenter == "sam3":
        return segment_open.Sam3Local()
    raise ValueError(f"unknown segmenter {cfg.segmenter!r}")


def judge(cfg: Config) -> StillJudge:
    if cfg.judge == "claude":
        from instep.providers.claude import ClaudeStillJudge

        return ClaudeStillJudge(model=cfg.judge_model, spend_cap_usd=cfg.spend_cap_usd)
    raise ValueError(f"unknown judge {cfg.judge!r}")
