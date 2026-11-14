import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from instep.eval.labels import load_labels
from instep.learner.events import (
    AMOUNT_DETAIL_KEYS,
    JUDGED_NOT_YET_DETAIL_KEYS,
    Event,
    needs_claim,
)


def test_needs_claim_splits_timer_and_judged_not_yet() -> None:
    assert needs_claim("amount", {}) == "amount"
    assert needs_claim("not_yet", {"timer": True}) is None
    assert needs_claim("not_yet", {"judged": True}) == "wait_until"


def test_ab_event_detail_shapes_are_stable() -> None:
    amount = Event(
        t_s=1.0,
        kind="amount",
        step_id="add_mustard",
        detail={
            "object": "mustard_seeds",
            "measure": "work_area_fraction",
            "learner_value": 0.5,
            "teacher_value": 0.08,
            "ok": False,
        },
    )
    assert AMOUNT_DETAIL_KEYS <= frozenset(amount.detail)
    judged = Event(
        t_s=2.0,
        kind="not_yet",
        step_id="add_mustard",
        detail={"judged": True, "condition": "the seeds start to pop", "confidence": 0.9},
    )
    assert JUDGED_NOT_YET_DETAIL_KEYS <= frozenset(judged.detail)


def test_event_rejects_unknown_kind() -> None:
    assert Event(t_s=3.0, kind="advance", step_id="add_mustard").kind == "advance"
    with pytest.raises(ValidationError):
        Event(t_s=3.0, kind="finished")


def labels(tmp_path: Path, confirmed_by: str | None) -> Path:
    data = {
        "recording": "learner_tadka_20261027_standin-chest.mp4",
        "lesson_id": "tadka-hand-min",
        "rows": [{"t_s": 12.0, "kind": "advance", "step_id": "add_mustard"}],
    }
    if confirmed_by is not None:
        data["confirmed_by"] = confirmed_by
    path = tmp_path / "labels.json"
    path.write_text(json.dumps(data))
    return path


def test_confirmed_labels_load(tmp_path: Path) -> None:
    assert load_labels(labels(tmp_path, "Arnav")).rows[0].step_id == "add_mustard"


@pytest.mark.parametrize("confirmed_by", [None, ""])
def test_unconfirmed_labels_are_refused(tmp_path: Path, confirmed_by: str | None) -> None:
    with pytest.raises(ValidationError, match="confirmed_by"):
        load_labels(labels(tmp_path, confirmed_by))
