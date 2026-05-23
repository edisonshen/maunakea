"""RunRecord persistence layer — the load-bearing memory primitive.

Every `Engine.suggest()` call writes a `RunRecord` to
`~/projects/maunakea/data/runs/<run_id>/` containing:

    prompt.txt      — the exact prompt sent to the model
    response.json   — parsed { research_suggestion, meta_suggestion, critique }
    meta.json       — RunRecord (timestamp, dataset_path, goal, model, ...)

Layout:

    data/
      runs/
        20260523-184213-a1b2c3/
          prompt.txt
          response.json
          meta.json

The data directory root can be overridden via `MAUNAKEA_DATA_DIR`.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, ValidationError


def _atomic_write_text(path: Path, content: str) -> None:
    """Write `content` to `path` atomically (write to .tmp then rename).

    Per CLAUDE.md: filesystem state must survive crashes. Without this, a
    process death between the three sequential writes in save_run could leave
    `data/runs/<id>/` with prompt.txt present but meta.json missing — which
    history() then ignores, masking the gap.
    """
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content)
    os.replace(tmp, path)


class RunRecord(BaseModel):
    run_id: str
    timestamp: str
    dataset_path: str
    goal: str
    model: str
    research_suggestion: str
    meta_suggestion: str
    critique: Optional[str] = None


def _data_dir() -> Path:
    return Path(
        os.environ.get(
            "MAUNAKEA_DATA_DIR",
            Path.home() / "projects" / "maunakea" / "data",
        )
    ).expanduser()


def save_run(
    *,
    dataset_path: str,
    goal: str,
    model: str,
    prompt: str,
    research_suggestion: str,
    meta_suggestion: str,
    critique: str | None = None,
) -> RunRecord:
    now = datetime.now(timezone.utc)
    run_id = f"{now.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
    record = RunRecord(
        run_id=run_id,
        timestamp=now.isoformat(),
        dataset_path=dataset_path,
        goal=goal,
        model=model,
        research_suggestion=research_suggestion,
        meta_suggestion=meta_suggestion,
        critique=critique,
    )
    out_dir = _data_dir() / "runs" / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    _atomic_write_text(out_dir / "prompt.txt", prompt)
    _atomic_write_text(
        out_dir / "response.json",
        json.dumps(
            {
                "research_suggestion": research_suggestion,
                "meta_suggestion": meta_suggestion,
                "critique": critique,
            },
            indent=2,
        ),
    )
    # meta.json last — its presence is the "this run is durable" signal that
    # load_runs() keys off; preceding files arriving first is the right order.
    _atomic_write_text(out_dir / "meta.json", record.model_dump_json(indent=2))
    return record


def load_runs(dataset_path: str | None = None) -> list[RunRecord]:
    runs_dir = _data_dir() / "runs"
    if not runs_dir.exists():
        return []
    records: list[RunRecord] = []
    target = str(Path(dataset_path).expanduser()) if dataset_path else None
    for d in sorted(runs_dir.iterdir()):
        meta = d / "meta.json"
        if not meta.exists():
            continue
        try:
            r = RunRecord.model_validate_json(meta.read_text())
        except (ValidationError, json.JSONDecodeError, OSError):
            # Skip corrupt / partially-written records rather than blow up the
            # whole history. A crash mid-save_run can land an unreadable
            # meta.json; we'd rather show N-1 good runs than zero.
            continue
        if target is None or r.dataset_path == target:
            records.append(r)
    return records
