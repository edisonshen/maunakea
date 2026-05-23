"""maunakea — generic recursive auto-improve system."""

from __future__ import annotations

__version__ = "0.0.1"

from .dataset import Dataset
from .engine import Engine, SuggestResult
from .goal import Goal, StructuredGoal
from .memory import RunRecord, load_runs, save_run

__all__ = [
    "__version__",
    "Dataset",
    "Engine",
    "Goal",
    "StructuredGoal",
    "SuggestResult",
    "RunRecord",
    "save_run",
    "load_runs",
]
