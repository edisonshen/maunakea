"""Engine behaviour — the recursive seed (A6), critique flag (A10), NIE stubs."""

from __future__ import annotations

import pytest

from maunakea import Dataset, Engine


def test_suggest_returns_both_fields(synthetic_cache, mock_litellm):
    ds = Dataset(synthetic_cache)
    e = Engine(ds, "predict 30-day forward returns")
    r = e.suggest()
    assert r.research_suggestion
    assert r.meta_suggestion
    assert r.critique is None
    assert r.run_id
    # Recursive seed: single LLM call produced both suggestions.
    assert mock_litellm.call_count == 1


def test_suggest_with_critique(synthetic_cache, mock_litellm):
    ds = Dataset(synthetic_cache)
    e = Engine(ds, "x")
    r = e.suggest(critique=True)
    assert r.critique is not None
    assert mock_litellm.call_count == 2


def test_run_raises(synthetic_cache):
    e = Engine(Dataset(synthetic_cache), "x")
    with pytest.raises(NotImplementedError):
        e.run()


def test_recurse_raises(synthetic_cache):
    e = Engine(Dataset(synthetic_cache), "x")
    with pytest.raises(NotImplementedError):
        e.recurse()


def test_structured_goal_serialises(synthetic_cache, mock_litellm):
    """StructuredGoal shell is declared (not run) but must serialise cleanly."""
    from maunakea import StructuredGoal

    g = StructuredGoal(target="fwd_30d_ret", features=["rank_5"], horizon=30)
    ds = Dataset(synthetic_cache)
    e = Engine(ds, g)
    r = e.suggest()
    assert r.run_id


def test_suggest_raises_on_non_json_response(synthetic_cache, mocker):
    """Trust boundary: LLM-returned non-JSON must surface as EngineParseError, not KeyError."""
    from maunakea.engine import EngineParseError

    def bad_completion(messages, response_format=None, **kwargs):
        resp = mocker.MagicMock()
        resp.choices = [mocker.MagicMock(message=mocker.MagicMock(content="not json at all"))]
        return resp

    mocker.patch("litellm.completion", side_effect=bad_completion)
    e = Engine(Dataset(synthetic_cache), "x")
    with pytest.raises(EngineParseError):
        e.suggest()


def test_suggest_raises_on_missing_field(synthetic_cache, mocker):
    """Trust boundary: JSON without meta_suggestion must NOT silently write a partial run."""
    from maunakea.engine import EngineParseError

    def partial_completion(messages, response_format=None, **kwargs):
        resp = mocker.MagicMock()
        resp.choices = [
            mocker.MagicMock(
                message=mocker.MagicMock(content='{"research_suggestion": "only one field"}')
            )
        ]
        return resp

    mocker.patch("litellm.completion", side_effect=partial_completion)
    e = Engine(Dataset(synthetic_cache), "x")
    with pytest.raises(EngineParseError):
        e.suggest()


def test_suggest_raises_on_empty_content(synthetic_cache, mocker):
    from maunakea.engine import EngineParseError

    def empty_completion(messages, response_format=None, **kwargs):
        resp = mocker.MagicMock()
        resp.choices = [mocker.MagicMock(message=mocker.MagicMock(content=""))]
        return resp

    mocker.patch("litellm.completion", side_effect=empty_completion)
    e = Engine(Dataset(synthetic_cache), "x")
    with pytest.raises(EngineParseError):
        e.suggest()
