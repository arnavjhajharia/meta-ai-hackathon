"""Configuration from environment variables (and .env). Which provider fills each role."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODELS = Path(os.environ.get("INSTEP_MODELS", Path.home() / ".cache" / "instep-models"))


def model_path(repo: str) -> str:
    """A local copy of a Hugging Face repo if we downloaded one, else the repo id."""
    local = MODELS / repo
    if (local / ".complete").exists():  # written after a verified download
        return str(local)
    return repo


def load_env() -> None:
    """Load .env into the process environment without overriding what is already set."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(ROOT / ".env", override=False)


@dataclass(frozen=True)
class Config:
    transcriber: str = "whisper-mlx"  # later: muse-voice
    whisper_model: str = "mlx-community/whisper-large-v3-turbo"
    understander: str = "claude"  # later: muse-spark
    draft_model: str = "claude-opus-5-5"
    draft_effort: str = "high"
    segmenter: str = "sam3"  # gdino-sam2 is the ungated fallback; later: sam3.1-hosted
    judge: str = "claude"
    judge_model: str = "claude-sonnet-5-5"
    spend_cap_usd: float = 50.0
    learner_fps: float = 1.0  # SAM 3 on the Mac is about 5 s a frame; raise on a real GPU
    tutorial_fps: float = 0.5

    @classmethod
    def from_env(cls) -> Config:
        load_env()
        defaults = cls()
        values = {}
        for name, default in defaults.__dict__.items():
            raw = os.environ.get(f"INSTEP_{name.upper()}")
            if raw is not None:
                values[name] = type(default)(raw)
        return cls(**values)
