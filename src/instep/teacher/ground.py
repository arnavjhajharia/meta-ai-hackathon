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

    def score(text: str) -> float:
        t = _norm(text)
        return fuzz.partial_ratio(q, t) if len(q) <= len(t) + 5 else 0.0

    best = QuoteMatch(0.0, None)
    for s in segs:
        sc = score(s.text)
        if sc > best.score:
            best = QuoteMatch(sc, s.start_s)
    if best.score >= QUOTE_MATCH:
        return best
    # only when no single segment holds it: a sentence straddling a boundary
    for a, b in zip(segs, segs[1:], strict=False):
        sc = score(a.text + " " + b.text)
        if sc > best.score:
            best = QuoteMatch(sc, a.start_s)
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
