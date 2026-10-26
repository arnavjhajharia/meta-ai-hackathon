"""Disk cache for anything that costs money or minutes, keyed by its exact inputs."""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

ROOT = Path(os.environ.get("INSTEP_CACHE", Path(__file__).resolve().parents[2] / ".cache"))


def key(**parts: Any) -> str:
    """Stable hash of the inputs. Bytes are hashed by content; everything else via JSON."""
    h = hashlib.sha256()
    for name in sorted(parts):
        value = parts[name]
        h.update(name.encode())
        if isinstance(value, bytes):
            h.update(hashlib.sha256(value).digest())
        else:
            h.update(json.dumps(value, sort_keys=True, default=str).encode())
    return h.hexdigest()[:32]


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def cached_json(
    namespace: str, k: str, compute: Callable[[], Any], root: Path | None = None
) -> Any:
    path = (root or ROOT) / namespace / f"{k}.json"
    if path.exists():
        return json.loads(path.read_text())
    value = compute()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(value))
    tmp.replace(path)
    return value


def cache_path(namespace: str, k: str, suffix: str, root: Path | None = None) -> Path:
    path = (root or ROOT) / namespace / f"{k}{suffix}"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path
