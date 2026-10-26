"""Scoring learner events against human-confirmed labels (data/labels/<clip stem>.json)."""

from __future__ import annotations

from pydantic import BaseModel

from instep.eval.labels import LabelFile
from instep.learner.events import Event

ADVANCE_TOL_S = 3.0
SKIP_TOL_S = 10.0
STALL_TOL_S = 10.0


class LearnerScore(BaseModel):
    advance_within_3s: float | None  # labelled advances matched by a system advance within 3 s
    advance_median_err_s: float | None
    advances_missed: int
    false_advances: int
    skips_caught: int
    skips_labelled: int
    false_skips: int
    stalls_caught: int
    stalls_labelled: int
    events_while_out_of_view: int
    false_events_per_min: float


def score(
    events: list[Event], labels: LabelFile, duration_s: float, out_of_view=()
) -> LearnerScore:
    def of(kind, items):
        return [x for x in items if x.kind == kind]

    adv_l, adv_e = of("advance", labels.rows), of("advance", events)
    used: set[int] = set()
    errs = []
    for row in adv_l:
        best = None
        for i, e in enumerate(adv_e):
            if i in used or e.step_id != row.step_id:
                continue
            d = abs(e.t_s - row.t_s)
            if best is None or d < best[1]:
                best = (i, d)
        if best is not None:
            used.add(best[0])
            errs.append(best[1])
    within = [e for e in errs if e <= ADVANCE_TOL_S]
    false_adv = len(adv_e) - len(used)

    def caught(kind, tol):
        lab, ev = of(kind, labels.rows), of(kind, events)
        hit, used_e = 0, set()
        for row in lab:
            for i, e in enumerate(ev):
                if i not in used_e and e.step_id == row.step_id and abs(e.t_s - row.t_s) <= tol:
                    hit += 1
                    used_e.add(i)
                    break
        return hit, len(lab), len(ev) - len(used_e)

    sk_hit, sk_n, sk_false = caught("skip", SKIP_TOL_S)
    st_hit, st_n, _ = caught("stall", STALL_TOL_S)
    progress_kinds = {"advance", "skip", "stall"}
    in_oov = sum(
        1
        for e in events
        if e.kind in progress_kinds and any(a + 1.0 < e.t_s < b for a, b in out_of_view)
    )
    minutes = max(duration_s / 60, 1e-6)
    return LearnerScore(
        advance_within_3s=round(len(within) / len(adv_l), 3) if adv_l else None,
        advance_median_err_s=round(sorted(errs)[len(errs) // 2], 2) if errs else None,
        advances_missed=len(adv_l) - len(errs),
        false_advances=false_adv,
        skips_caught=sk_hit,
        skips_labelled=sk_n,
        false_skips=sk_false,
        stalls_caught=st_hit,
        stalls_labelled=st_n,
        events_while_out_of_view=in_oov,
        false_events_per_min=round((false_adv + sk_false) / minutes, 2),
    )
