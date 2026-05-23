"""Shared pytest fixtures.

`rainier_cache` skips when the operator's local rainier parquet directory is
absent — keeps maunakea CI green even on a fresh clone where rainier isn't
sitting next door. For CI, `synthetic_cache` builds a minimal parquet fixture
on the fly so the parquet-touching tests still exercise real code paths.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest


@pytest.fixture
def rainier_cache() -> Path:
    p = Path.home() / "projects" / "rainier" / "data" / "cache"
    if not p.exists():
        pytest.skip(f"rainier cache not at {p}")
    return p


@pytest.fixture
def synthetic_cache(tmp_path: Path) -> Path:
    """A minimal parquet dataset that matches the four-table contract A5 cares about.

    Each table is one row — just enough to exercise list/columns/load without
    a real rainier cache present.
    """
    cache = tmp_path / "cache"
    cache.mkdir()
    pd.DataFrame(
        {"symbol": ["AAPL"], "asof_date": ["2026-05-23"], "rank_5": [1.0]}
    ).to_parquet(cache / "thematic_features_daily.parquet")
    pd.DataFrame(
        {"symbol": ["AAPL"], "asof_date": ["2026-05-23"], "fwd_30d_ret": [0.01]}
    ).to_parquet(cache / "thematic_labels_daily.parquet")
    pd.DataFrame({"symbol": ["AAPL"], "asof_date": ["2026-05-23"]}).to_parquet(
        cache / "thematic_universe.parquet"
    )
    pd.DataFrame({"asof_date": ["2026-05-23"], "vix": [16.0]}).to_parquet(
        cache / "macro_context.parquet"
    )
    return cache


@pytest.fixture
def mock_litellm(mocker):
    """Stub litellm.completion with structured JSON output.

    The first system prompt (research planner) returns both
    `research_suggestion` and `meta_suggestion`; the critique prompt returns
    a single `critique` field.
    """

    def fake_completion(messages, response_format=None, **kwargs):
        system = messages[0]["content"]
        if "research_suggestion" in system:
            content = (
                '{"research_suggestion": "run OLS of fwd_30d_ret on rank_5/10/20", '
                '"meta_suggestion": "add VIX regime context"}'
            )
        else:
            content = '{"critique": "rank-based features may overfit to recent regime"}'
        resp = mocker.MagicMock()
        resp.choices = [mocker.MagicMock(message=mocker.MagicMock(content=content))]
        return resp

    return mocker.patch("litellm.completion", side_effect=fake_completion)


@pytest.fixture(autouse=True)
def tmp_data_dir(tmp_path, monkeypatch):
    """Redirect MAUNAKEA_DATA_DIR to tmp_path so tests don't pollute real data dir."""
    monkeypatch.setenv("MAUNAKEA_DATA_DIR", str(tmp_path))
    return tmp_path
