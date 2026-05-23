"""Memory layer — persistence (A9) + history round-trip (A8)."""

from __future__ import annotations

import json

from maunakea import Dataset, Engine


def test_suggest_persists_run(synthetic_cache, mock_litellm, tmp_data_dir):
    ds = Dataset(synthetic_cache)
    e = Engine(ds, "x")
    r = e.suggest()
    run_dir = tmp_data_dir / "runs" / r.run_id
    assert (run_dir / "prompt.txt").exists()
    assert (run_dir / "response.json").exists()
    assert (run_dir / "meta.json").exists()


def test_response_json_has_recursive_seed(synthetic_cache, mock_litellm, tmp_data_dir):
    """Both suggestions are durably written to response.json — Phase 3 consumer."""
    ds = Dataset(synthetic_cache)
    e = Engine(ds, "x")
    r = e.suggest()
    payload = json.loads(
        (tmp_data_dir / "runs" / r.run_id / "response.json").read_text()
    )
    assert payload["research_suggestion"]
    assert payload["meta_suggestion"]


def test_history_reads_past_runs(synthetic_cache, mock_litellm):
    ds = Dataset(synthetic_cache)
    e = Engine(ds, "x")
    r = e.suggest()
    past = e.history()
    assert any(rec.run_id == r.run_id for rec in past)


def test_history_filters_by_dataset_path(synthetic_cache, mock_litellm, tmp_path):
    """A dataset at a different path should not see prior dataset's runs."""
    import pandas as pd

    other = tmp_path / "other"
    other.mkdir()
    pd.DataFrame({"a": [1]}).to_parquet(other / "t.parquet")

    e1 = Engine(Dataset(synthetic_cache), "x")
    r1 = e1.suggest()

    e2 = Engine(Dataset(other), "y")
    past2 = e2.history()
    assert all(rec.run_id != r1.run_id for rec in past2)


def test_history_skips_corrupt_meta(synthetic_cache, mock_litellm, tmp_data_dir):
    """A half-written meta.json must not break history(); the good runs still surface."""
    ds = Dataset(synthetic_cache)
    e = Engine(ds, "x")
    good = e.suggest()
    # Plant a corrupt sibling.
    corrupt_dir = tmp_data_dir / "runs" / "99999999-000000-deadbe"
    corrupt_dir.mkdir(parents=True)
    (corrupt_dir / "meta.json").write_text("{ this is not json")
    past = e.history()
    assert any(r.run_id == good.run_id for r in past)


def test_save_run_is_atomic(synthetic_cache, mock_litellm, tmp_data_dir):
    """Each persisted file must arrive whole (.tmp files never linger on success)."""
    ds = Dataset(synthetic_cache)
    e = Engine(ds, "x")
    r = e.suggest()
    run_dir = tmp_data_dir / "runs" / r.run_id
    stale_tmps = list(run_dir.glob("*.tmp"))
    assert not stale_tmps, f"stale .tmp files left behind: {stale_tmps}"
