"""Hold the model to what the recording contains. No model calls here."""

from __future__ import annotations

from dataclasses import dataclass

from rapidfuzz import fuzz

from instep.providers.base import DraftTip, Transcript

QUOTE_MATCH = 85  # rapidfuzz partial_ratio, 0 to 100


@dataclass
class QuoteMatch:
    score: float
    start_s: float | None


def find_quote(quote: str, transcript: Transcript | None) -> QuoteMatch:
    """Best fuzzy match of a quote in the transcript, by segment and by pairs of segments
    (a spoken sentence can straddle a segment boundary)."""
    if not transcript or not transcript.segments or not quote.strip():
        return QuoteMatch(0.0, None)
    q = _norm(quote)
    segs = transcript.segments
    best = QuoteMatch(0.0, None)
    for i, s in enumerate(segs):
        for text in (s.text, s.text + " " + segs[i + 1].text if i + 1 < len(segs) else None):
            if text is None:
                continue
            score = fuzz.partial_ratio(q, _norm(text)) if len(q) <= len(text) + 5 else 0.0
            if score > best.score:
                best = QuoteMatch(score, s.start_s)
    return best


def ground_tip(tip: DraftTip, transcript: Transcript | None) -> tuple[DraftTip | None, str | None]:
    """Keep a tip only if it is grounded. Returns (tip or None, issue or None)."""
    if tip.source == "action":
        return tip, None
    if tip.source == "caption":
        # on-screen text is checked by the reviewer against the frame, not here
        return (
            (tip, None)
            if tip.quote
            else (None, f"caption tip without its text dropped: {tip.text!r}")
        )
    if not tip.quote:
        return None, f"spoken tip without a quote dropped: {tip.text!r}"
    match = find_quote(tip.quote, transcript)
    if match.score < QUOTE_MATCH:
        return None, f"quote not in transcript ({match.score:.0f}): {tip.quote!r}"
    if match.start_s is not None and abs(match.start_s - tip.at_s) > 8:
        return tip.model_copy(update={"at_s": match.start_s}), (
            f"tip time moved {tip.at_s:.1f}s -> {match.start_s:.1f}s to where it was said"
        )
    return tip, None


def _norm(text: str) -> str:
    return " ".join(text.lower().replace(",", " ").replace(".", " ").split())
