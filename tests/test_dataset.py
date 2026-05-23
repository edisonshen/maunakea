"""Dataset adapter tests.

A5 names rainier's four core tables — when the operator's local rainier
cache is present we assert against it directly. CI uses `synthetic_cache`
to exercise the same code paths without a rainier dependency.
"""

from __future__ import annotations

from maunakea import Dataset


def test_list_against_rainier(rainier_cache):
    ds = Dataset(rainier_cache)
    names = ds.list()
    for req in (
        "thematic_features_daily",
        "thematic_labels_daily",
        "thematic_universe",
        "macro_context",
    ):
        assert req in names


def test_load_thematic_features(rainier_cache):
    ds = Dataset(rainier_cache)
    df = ds.load("thematic_features_daily")
    assert len(df) > 0
    assert "symbol" in df.columns and "asof_date" in df.columns


def test_list_against_synthetic(synthetic_cache):
    ds = Dataset(synthetic_cache)
    names = ds.list()
    for req in (
        "thematic_features_daily",
        "thematic_labels_daily",
        "thematic_universe",
        "macro_context",
    ):
        assert req in names


def test_load_synthetic_features(synthetic_cache):
    ds = Dataset(synthetic_cache)
    df = ds.load("thematic_features_daily")
    assert len(df) > 0
    assert "symbol" in df.columns and "asof_date" in df.columns


def test_columns_and_sample(synthetic_cache):
    ds = Dataset(synthetic_cache)
    cols = ds.columns("thematic_features_daily")
    assert "symbol" in cols
    sample = ds.sample("thematic_features_daily", n=1)
    assert len(sample) == 1


def test_missing_path_raises(tmp_path):
    import pytest

    with pytest.raises(FileNotFoundError):
        Dataset(tmp_path / "does-not-exist")


def test_missing_table_raises(synthetic_cache):
    import pytest

    ds = Dataset(synthetic_cache)
    with pytest.raises(FileNotFoundError):
        ds.load("not_a_real_table")
