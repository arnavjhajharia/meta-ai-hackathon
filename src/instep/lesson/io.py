"""Load and save Lessons, and export the committed JSON Schema.

Regenerate the schema after changing the models: .venv/bin/python -m instep.lesson.io
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from instep.lesson.schema import SCHEMA_VERSION, Lesson

SCHEMA_PATH = Path(__file__).resolve().parents[3] / "schemas" / f"lesson.v{SCHEMA_VERSION}.json"


class UnsupportedSchemaVersion(ValueError):
    pass


def load_lesson(path: Path) -> Lesson:
    data = json.loads(Path(path).read_text())
    version = data.get("schema_version")
    if version != SCHEMA_VERSION:
        raise UnsupportedSchemaVersion(
            f"{path}: schema_version {version!r}, this code reads {SCHEMA_VERSION!r}"
        )
    return Lesson.model_validate(data)


def save_lesson(lesson: Lesson, path: Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(lesson.model_dump_json(indent=2) + "\n")


def json_schema() -> dict[str, Any]:
    return Lesson.model_json_schema()


def export_schema(path: Path = SCHEMA_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_schema(), indent=2) + "\n")


if __name__ == "__main__":
    export_schema()
    print(f"wrote {SCHEMA_PATH}")
