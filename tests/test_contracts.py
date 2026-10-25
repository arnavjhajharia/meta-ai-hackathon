import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from instep.eval.labels import load_labels
from instep.learner.events import Event


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
