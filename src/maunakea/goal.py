"""Research goal — NL for MVP; typed for future structured spec.

`Goal` is a `Union[str, StructuredGoal]`. The MVP only exercises the `str`
branch; `StructuredGoal` is declared so the API can promise both shapes for
forward-compat.
"""

from __future__ import annotations

from typing import Union

from pydantic import BaseModel, Field


class StructuredGoal(BaseModel):
    """Future structured-goal shape. Declared, not implemented in MVP code paths."""

    target: str = Field(description="Variable to predict / explain.")
    features: list[str] = Field(default_factory=list)
    horizon: int | None = None
    constraint: str | None = None


Goal = Union[str, StructuredGoal]
