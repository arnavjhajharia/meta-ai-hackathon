from datetime import UTC, datetime

from instep.lesson.schema import MadeBy, RecordingRef
from instep.providers.base import DraftLesson, Segment, Transcript
from instep.teacher.draft import to_lesson
from instep.teacher.ground import find_quote

REC = RecordingRef(
    path="data/recordings/tutorial_paper-boat_youtube_abc.mp4",
    sha256="0" * 64,
    duration_s=60.0,
    fps=30,
    width=1280,
    height=720,
)
BY = MadeBy(
    understanding="fake",
    segmenter="none",
    transcriber="fake",
    pipeline_version="t",
    created_at=datetime(2026, 10, 26, tzinfo=UTC),
)
TRANSCRIPT = Transcript(
    language="hi",
    segments=[
        Segment(start_s=10.0, end_s=13.0, text="ab isko beech se mod do"),
        Segment(start_s=30.0, end_s=33.0, text="kone ko andar daalo"),
    ],
)


def draft(**overrides) -> DraftLesson:
    base = {
        "title": "Paper boat",
        "task": "paper-boat",
        "language": "hi",
        "objects": [
            {"id": "paper", "prompt": "Square Paper", "role": "work_area", "confusable_with": []},
            {"id": "hand", "prompt": "hand", "role": "hand", "confusable_with": ["ghost"]},
        ],
        "work_area_object": "paper",
        "steps": [
            {
                "id": "fold half",
                "title": "Fold in half",
                "instruction": "Fold the paper in half — edge to edge.",
                "start_s": 8.0,
                "end_s": 15.0,
                "objects": ["paper", "scissors"],
                "completion_kind": "appears_in_work_area",
                "completion_object": None,
                "end_state": "paper folded into a rectangle",
                "reference_frame_s": 14.3,
                "tips": [
                    {
                        "text": "Fold it from the middle.",
                        "quote": "isko beech se mod do",
                        "quote_language": "hi",
                        "source": "speech",
                        "at_s": 11.0,
                    },
                    {
                        "text": "Press hard.",
                        "quote": "zor se dabao",
                        "quote_language": "hi",
                        "source": "speech",
                        "at_s": 12.0,
                    },
                ],
                "optional": False,
            },
            {
                "id": "tuck",
                "title": "Tuck the corner",
                "instruction": "Tuck the corner inside.",
                "start_s": 12.0,
                "end_s": 34.0,
                "objects": ["paper"],
                "completion_kind": "end_state",
                "completion_object": None,
                "end_state": "corner hidden inside",
                "reference_frame_s": 34.0,
                "tips": [
                    {
                        "text": "Use a ruler edge.",
                        "quote": "Use scale for sharp fold",
                        "quote_language": "en",
                        "source": "caption",
                        "at_s": 31.0,
                    }
                ],
                "optional": False,
            },
        ],
        "not_part_of_task": [],
    }
    base.update(overrides)
    return DraftLesson.model_validate(base)


def convert(d: DraftLesson):
    return to_lesson(d, REC, TRANSCRIPT, BY, frame_times=[float(t) for t in range(0, 60, 2)])


def test_conversion_repairs_and_reports() -> None:
    lesson, issues = convert(draft())
    s0, s1 = lesson.steps
    assert lesson.id == "paper-boat-abc"
    assert lesson.object("paper").prompt == "square paper"
    assert lesson.object("hand").confusable_with == []
    assert s0.id == "fold_half" and "scissors" not in s0.objects
    assert s0.completion.kind == "end_state"  # appears_in_work_area without an object
    assert "—" not in s0.instruction
    assert s0.completion.reference_frame_s == 14.0  # snapped to a frame we sent
    assert [t.text for t in s0.tips] == ["Fold it from the middle."]
    assert s1.span_model.start_s == 15.0  # overlap removed
    assert s1.tips[0].source == "caption"
    joined = " | ".join(issues)
    for expected in ("unknown objects", "now end_state", "not in transcript", "overlapped"):
        assert expected in joined


def test_quote_matching_tolerates_small_differences() -> None:
    assert find_quote("isko beech se modo", TRANSCRIPT).score >= 85
    assert find_quote("add two spoons of sugar", TRANSCRIPT).score < 85


def test_missing_work_area_is_added() -> None:
    lesson, issues = convert(draft(work_area_object="steel tray"))
    assert lesson.work_area_object == "steel_tray"
    assert lesson.object("steel_tray").role == "work_area"
    assert lesson.object("paper").role == "container"
    assert any("not among objects" in i for i in issues)


def test_quote_time_prefers_the_segment_that_holds_it() -> None:
    t = Transcript(
        language="en",
        segments=[
            Segment(start_s=8.9, end_s=18.9, text="please read my disclaimer below"),
            Segment(
                start_s=18.9, end_s=25.0, text="there may be a fracture that you don't know about"
            ),
        ],
    )
    assert find_quote("there may be a fracture that you don't know about", t).start_s == 18.9
    assert find_quote("disclaimer below there may be", t).start_s == 8.9
