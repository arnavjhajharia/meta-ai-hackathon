import copy
import json
from collections.abc import Callable
from pathlib import Path

import pytest
from pydantic import ValidationError

from instep.lesson.io import (
    SCHEMA_PATH,
    UnsupportedSchemaVersion,
    json_schema,
    load_lesson,
    save_lesson,
)
from instep.lesson.schema import Claim, Lesson

FIXTURES = Path(__file__).parent / "fixtures"


def raw(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


GLASSES = "lesson_glasses_min.json"
PHONE = "lesson_phone_min.json"


def rejected(name: str, mutate: Callable[[dict], None], match: str) -> None:
    data = copy.deepcopy(raw(name))
    mutate(data)
    with pytest.raises(ValidationError, match=match):
        Lesson.model_validate(data)


@pytest.mark.parametrize("name", [GLASSES, PHONE])
def test_fixture_round_trips(name: str, tmp_path: Path) -> None:
    lesson = load_lesson(FIXTURES / name)
    out = tmp_path / "lesson.json"
    save_lesson(lesson, out)
    assert load_lesson(out) == lesson


def test_claims_follow_the_recording() -> None:
    glasses = load_lesson(FIXTURES / GLASSES)
    phone = load_lesson(FIXTURES / PHONE)
    assert glasses.claims() == set(Claim)
    assert phone.claims() == {Claim.presence, Claim.order, Claim.progress}


def test_glasses_lesson_filmed_from_a_fixed_camera_gets_coarse_claims() -> None:
    data = raw(GLASSES)
    data["provenance"]["viewpoint"] = "third_person"
    for step in data["steps"]:
        step["amount"] = None
        step["wait_until"] = None
    assert Claim.amount not in Lesson.model_validate(data).claims()


def test_phone_lesson_with_amount_is_rejected() -> None:
    def add_amount(d: dict) -> None:
        d["steps"][0]["amount"] = {
            "object": "mustard_seeds",
            "measure": "work_area_fraction",
            "teacher_value": 0.1,
            "tolerance": 0.3,
        }

    rejected(PHONE, add_amount, "amount")


def test_phone_lesson_with_wait_until_is_rejected() -> None:
    def add_wait(d: dict) -> None:
        d["steps"][0]["wait_until"] = {
            "condition": "the seeds pop",
            "still_checkable": True,
            "reference_frame_s": 14.0,
            "cue_not_yet": "Not yet.",
        }

    rejected(PHONE, add_wait, "wait_until")


def test_duplicate_step_id_is_rejected() -> None:
    rejected(GLASSES, lambda d: d["steps"][1].update(id="add_mustard"), "duplicate step id")


def test_duplicate_object_id_is_rejected() -> None:
    rejected(GLASSES, lambda d: d["objects"][2].update(id="mustard_seeds"), "duplicate object id")


def test_unknown_object_reference_is_rejected() -> None:
    rejected(GLASSES, lambda d: d["steps"][0]["objects"].append("ghee"), "ghee")
    rejected(GLASSES, lambda d: d["steps"][0]["completion"].update(object="ghee"), "ghee")
    rejected(GLASSES, lambda d: d["steps"][0]["amount"].update(object="ghee"), "ghee")
    rejected(GLASSES, lambda d: d["objects"][1].update(confusable_with=["ghee"]), "ghee")


def test_work_area_must_be_a_work_area_object() -> None:
    rejected(GLASSES, lambda d: d.update(work_area_object="curry_leaves"), "work_area")


def test_step_index_must_match_position() -> None:
    rejected(GLASSES, lambda d: d["steps"][1].update(index=5), "index")


def test_steps_must_be_in_time_order() -> None:
    rejected(GLASSES, lambda d: d["steps"][1].update(span={"start_s": 2.0, "end_s": 4.0}), "order")


def test_span_must_have_positive_length() -> None:
    rejected(GLASSES, lambda d: d["steps"][0].update(span={"start_s": 5.0, "end_s": 5.0}), "end_s")


def test_span_must_fit_inside_recording() -> None:
    rejected(PHONE, lambda d: d["steps"][1].update(span={"start_s": 50.0, "end_s": 70.0}), "70")
    rejected(PHONE, lambda d: d["steps"][0]["tips"][0].update(at_s=99.0), "99")


def test_spoken_tip_needs_a_quote() -> None:
    rejected(PHONE, lambda d: d["steps"][0]["tips"][0].update(quote=None), "quote")


def test_pipeline_lesson_needs_a_recording() -> None:
    rejected(PHONE, lambda d: d["provenance"].update(recording=None), "recording")
    rejected(PHONE, lambda d: d["provenance"].update(made_by=None), "made_by")


def test_learner_facing_text_has_no_em_dashes() -> None:
    rejected(GLASSES, lambda d: d["steps"][0].update(title="Seeds — now"), "em dash")
    rejected(
        GLASSES,
        lambda d: d["steps"][0]["wait_until"].update(cue_not_yet="Not yet — wait."),
        "em dash",
    )


def test_unknown_fields_are_rejected() -> None:
    rejected(GLASSES, lambda d: d["steps"][0].update(colour="red"), "colour")


def test_unknown_schema_version_is_rejected(tmp_path: Path) -> None:
    data = raw(GLASSES)
    data["schema_version"] = "2"
    path = tmp_path / "lesson.json"
    path.write_text(json.dumps(data))
    with pytest.raises(UnsupportedSchemaVersion):
        load_lesson(path)


def test_committed_json_schema_matches_the_models() -> None:
    committed = json.loads(SCHEMA_PATH.read_text())
    assert committed == json_schema(), (
        "schemas/lesson.v1.json is stale. Regenerate: .venv/bin/python -m instep.lesson.io"
    )
