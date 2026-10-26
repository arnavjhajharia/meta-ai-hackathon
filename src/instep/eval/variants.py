"""Compare draft prompt variants on the same tutorials, on checks that need no labels.

  python -m instep.eval.variants [--videos a.mp4 b.mp4 ...] [--variants V1 V2 ...] [--max-usd 6]

Prints and writes a table to runs/eval/variants_<time>.md. Stops before going over --max-usd of
new (uncached) spend. Without confirmed step lists this ranks variants on hygiene and agreement,
not correctness: say so when reporting.
"""

from __future__ import annotations

import argparse
import itertools
import time
from pathlib import Path

from instep.cli import RUNS, build_lesson, parse_variant
from instep.config import ROOT
from instep.eval.teacher import auto_score, consistency, load_reference, ref_score
from instep.providers.claude import SpendCapReached, spent_usd

DEFAULT_VARIANTS = [
    "draft_v1:2:120:512:tx",
    "draft_v2:2:120:512:tx",
    "draft_v1:4:60:512:tx",
    "draft_v1:2:120:512:notx",
]


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--videos", nargs="*", type=Path)
    ap.add_argument("--variants", nargs="*", default=DEFAULT_VARIANTS)
    ap.add_argument("--max-usd", type=float, default=6.0)
    ap.add_argument("--calibrate", action="store_true")
    args = ap.parse_args(argv)
    videos = args.videos or sorted((ROOT / "data" / "recordings").glob("tutorial_*.mp4"))

    start_spend = spent_usd()
    rows, lessons = [], {}
    for video, variant in itertools.product(videos, args.variants):
        if spent_usd() - start_spend >= args.max_usd:
            print(f"stopping: ${spent_usd() - start_spend:.2f} new spend reached the limit")
            break
        try:
            lesson, report = build_lesson(video, parse_variant(variant), args.calibrate)
        except SpendCapReached as e:
            print(f"stopping: {e}")
            break
        lessons[(video.stem, variant)] = lesson
        auto = auto_score(lesson, report)
        ref_path = ROOT / "data" / "labels" / "tutorials" / f"{video.stem}.json"
        ref = ref_score(lesson, load_reference(ref_path)) if ref_path.exists() else None
        rows.append((video.stem, variant, auto, ref))
        print(video.stem, variant, auto.model_dump(), ref.model_dump() if ref else "")

    agreement = {}
    for stem in {r[0] for r in rows}:
        mine = [(v, lessons[(stem, v)]) for v in args.variants if (stem, v) in lessons]
        for (va, la), (vb, lb) in itertools.combinations(mine, 2):
            agreement[(stem, va, vb)] = consistency(la, lb)

    out = RUNS / "eval" / f"variants_{time.strftime('%Y%m%d_%H%M%S')}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "| video | variant | steps | repairs | tips kept | tips dropped | vague | end_state |"
        " findable | recall | precision | within 3 s |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for stem, variant, a, r in rows:
        lines.append(
            f"| {stem.split('_youtube_')[0].removeprefix('tutorial_')} | {variant} | {a.n_steps} |"
            f" {a.repairs} | {a.tips_kept} | {a.tips_dropped} | {a.vague_prompts} |"
            f" {a.end_state_steps} | {'' if a.findability_mean is None else a.findability_mean}"
            f" |"
            f" {r.recall if r else ''} | {r.precision if r else ''} | {r.within_3s if r else ''} |"
        )
    lines += ["", "Agreement between variants (1.0 = same steps at the same times):", ""]
    lines += [f"- {s.split('_youtube_')[0]}: {a} vs {b}: {v}" for (s, a, b), v in agreement.items()]
    lines += ["", f"New spend: ${spent_usd() - start_spend:.2f}"]
    out.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(out)


if __name__ == "__main__":
    main()
