from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from production_agent_2.paths import RUNS_ROOT


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def ensure_run_dirs(run_id: str) -> dict[str, Path]:
    base = RUNS_ROOT / run_id
    dirs = {
        "base": base,
        "artifacts": base / "artifacts",
        "boards": base / "artifacts" / "reference_boards",
        "outputs": base / "outputs",
        "state": base / "state",
    }
    for path in dirs.values():
        path.mkdir(parents=True, exist_ok=True)
    return dirs


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
