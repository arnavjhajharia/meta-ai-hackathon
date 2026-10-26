"""Local Whisper on Apple Silicon (stand-in for Muse Voice Transcribe)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from instep import cache
from instep.providers.base import Segment, Transcript, Word


@dataclass
class MlxWhisper:
    model: str = "mlx-community/whisper-large-v3-turbo"
    name: str = "whisper-mlx"

    def transcribe(self, media_path: Path) -> Transcript:
        k = cache.key(provider=self.name, model=self.model, media=cache.file_sha256(media_path))
        data = cache.cached_json("transcribe", k, lambda: self._run(media_path))
        return Transcript.model_validate(data)

    def _run(self, media_path: Path) -> dict:
        import mlx_whisper

        from instep.config import model_path

        result = mlx_whisper.transcribe(
            str(media_path),
            path_or_hf_repo=model_path(self.model),
            word_timestamps=True,
            condition_on_previous_text=False,  # fewer runaway repetitions on music-heavy videos
        )
        segments = []
        for s in result["segments"]:
            text = s["text"].strip()
            # drop silence and music the model hallucinates text over
            if not text or s.get("no_speech_prob", 0) > 0.6 and s.get("avg_logprob", 0) < -1:
                continue
            words = [
                Word(start_s=w["start"], end_s=w["end"], text=w["word"].strip())
                for w in s.get("words", [])
            ]
            segments.append(Segment(start_s=s["start"], end_s=s["end"], text=text, words=words))
        return Transcript(language=result.get("language"), segments=segments).model_dump()
