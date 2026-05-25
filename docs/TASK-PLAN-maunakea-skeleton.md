# TASK PLAN: maunakea — Phase 1 MVP

- **Parent design:** [DESIGN-split-research-to-maunakea.md](DESIGN-split-research-to-maunakea.md) §5 Phase 1
- **Slug:** `maunakea-skeleton` (it's an end-to-end MVP, not just skeleton)
- **Priority:** P1
- **Owner:** dispatched subagent (general-purpose Agent)
- **Coord:** projects-rainier coord (`c02eab1f`)
- **Status:** Drafted v5 (locked); pending operator dispatch sign-off
- **Date:** 2026-05-23

---

## 1. Goal

Bootstrap the `maunakea` repo as a **public, generic, recursive auto-improve system**. The MVP ships:

- A clean Dataset / Goal / Engine API (domain-agnostic).
- A CLI: `maunakea suggest --dataset <path> --goal "<NL>"` and `maunakea history --dataset <path>`.
- Persistent `RunRecord`s on disk — every `suggest()` saves its prompt, response, and meta_suggestion.
- The recursive seed: every LLM call produces *both* a research suggestion AND a self-improvement suggestion in the same structured-JSON response.
- Zero `rainier` Python dep. CI-enforced via grep.
- A public-facing README + ARCHITECTURE.md so external readers (e.g., people arriving via [fengshen.dev/recursive](https://fengshen.dev/recursive/)) can understand the project.

After Phase 1 lands, the operator can immediately dogfood against rainier's QU100 parquets via the generic CLI. Trading-specific wrappers (`picks`/`track`/`backtest`) are a Phase 4 follow-up that lives in rainier, not maunakea.

---

## 2. Acceptance criteria

| # | Criterion | Verification |
|---|---|---|
| A1 | Repo at `~/projects/maunakea/` with `.git/` initialised | `ls -d ~/projects/maunakea/.git` |
| A2 | GitHub repo `edisonshen/maunakea` created **PUBLIC** with **MIT license**, origin pushed | `gh repo view edisonshen/maunakea --json visibility,licenseInfo` |
| A3 | `uv run maunakea --version` prints `0.0.1` | from `~/projects/maunakea/` |
| A4 | **Decoupling:** `rg "rainier" src/maunakea/` returns zero matches | grep |
| A5 | `Dataset(~/projects/rainier/data/cache/).list()` returns ≥ the 4 core tables (`thematic_features_daily`, `thematic_labels_daily`, `thematic_universe`, `macro_context`); `.load("thematic_features_daily")` returns non-empty DataFrame with `symbol` + `asof_date` columns | smoke test |
| A6 | `Engine.suggest()` returns a `SuggestResult` with both `research_suggestion: str` AND `meta_suggestion: str` populated. Implementation: one `litellm.completion` call with structured JSON output. Mocked in CI. | smoke test |
| A7 | `maunakea suggest --dataset <rainier-cache> --goal "<NL>"` CLI exits 0; stdout contains both `Research suggestion:` and `Meta-suggestion:` sections | smoke test (mocked LLM) |
| A8 | `maunakea history --dataset <rainier-cache>` reads past runs from disk; smoke test verifies a freshly-written `RunRecord` round-trips | smoke test |
| A9 | Every `suggest()` call writes a `RunRecord` to `~/projects/maunakea/data/runs/<run_id>/` containing: `prompt.txt`, `response.json`, `meta.json` (timestamp, dataset_path, goal, model) | smoke test inspects directory |
| A10 | `--critique` flag triggers a second mocked LLM call; result includes a `critique: str | None` field | smoke test |
| A11 | First CI run on initial push is green: build smoke + ruff + pytest + **decoupling grep** | `gh run list --limit 1` |
| A12 | `README.md` contains: one-paragraph framing, install instructions, link to design doc, prior-art list (Promptbreeder, AlphaEvolve, OpenEvolve, AI Scientist, SWE-agent), link to [fengshen.dev/recursive](https://fengshen.dev/recursive/). `docs/ARCHITECTURE.md` exists with the three-layer (LLM + framework + harness) diagram | `grep -q "Promptbreeder" README.md && test -f docs/ARCHITECTURE.md` |

A1–A12 must all pass before the worker reports done.

---

## 3. Files to create

```
~/projects/maunakea/
├── .gitignore
├── .python-version
├── CLAUDE.md                    # framework rules; thin-harness principle; decoupling invariant
├── LICENSE                      # MIT
├── README.md                    # public-facing: framing + install + prior art + links
├── VERSION                      # 0.0.1
├── pyproject.toml               # NO rainier dep
├── ruff.toml                    # copy rainier
├── .github/workflows/ci.yml     # build + ruff + pytest + decoupling-grep
├── docs/
│   └── ARCHITECTURE.md          # three-layer model; pillar mapping; phase roadmap
├── src/maunakea/
│   ├── __init__.py              # __version__; re-exports Dataset, Goal, Engine, SuggestResult
│   ├── cli.py                   # click: --version, suggest, history
│   ├── dataset.py               # Dataset(path); list/columns/sample/load
│   ├── goal.py                  # Goal = Union[str, StructuredGoal]
│   ├── engine.py                # Engine.suggest(critique=False), .history(), .run() NIE, .recurse() NIE
│   └── memory.py                # RunRecord (Pydantic), save_run(), load_runs()
└── tests/
    ├── __init__.py
    ├── conftest.py              # rainier_cache fixture + mock_litellm fixture
    ├── test_dataset.py
    ├── test_engine.py
    ├── test_memory.py
    └── test_smoke.py
```

### 3.1 `pyproject.toml` (target)

```toml
[project]
name = "maunakea"
version = "0.0.1"
description = "Generic recursive auto-improve system. Inputs: dataset path + goal."
requires-python = ">=3.11"
license = "MIT"
dependencies = [
    "pandas",
    "pyarrow",
    "click",
    "pydantic>=2",
    "litellm",
]

[project.optional-dependencies]
dev = ["pytest", "pytest-mock", "ruff"]

[project.scripts]
maunakea = "maunakea.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/maunakea"]
```

**No `[tool.uv.sources]` rainier entry. No editable install.**

### 3.2 `dataset.py` (target)

```python
"""Generic dataset adapter. Parquet-only in MVP."""

from __future__ import annotations
from pathlib import Path
import pandas as pd


class Dataset:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).expanduser()
        if not self.path.exists():
            raise FileNotFoundError(f"dataset path does not exist: {self.path}")

    def list(self) -> list[str]:
        if self.path.is_file():
            return [self.path.stem]
        return sorted(p.stem for p in self.path.glob("*.parquet"))

    def _resolve(self, name: str) -> Path:
        if self.path.is_file():
            return self.path
        candidate = self.path / f"{name}.parquet"
        if not candidate.exists():
            raise FileNotFoundError(
                f"{name}.parquet not in {self.path}. Available: {', '.join(self.list())}"
            )
        return candidate

    def columns(self, name: str) -> list[str]:
        import pyarrow.parquet as pq
        return list(pq.read_schema(self._resolve(name)).names)

    def sample(self, name: str, n: int = 10) -> pd.DataFrame:
        return self.load(name).head(n)

    def load(self, name: str) -> pd.DataFrame:
        return pd.read_parquet(self._resolve(name))
```

### 3.3 `goal.py` (target)

```python
"""Research goal — NL for MVP; typed for future structured spec."""

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
```

### 3.4 `memory.py` (target)

```python
"""RunRecord persistence layer — the load-bearing memory primitive."""

from __future__ import annotations
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from pydantic import BaseModel


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
    import os
    return Path(os.environ.get("MAUNAKEA_DATA_DIR",
                               Path.home() / "projects" / "maunakea" / "data")).expanduser()


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
    run_id = f"{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
    record = RunRecord(
        run_id=run_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        dataset_path=dataset_path,
        goal=goal,
        model=model,
        research_suggestion=research_suggestion,
        meta_suggestion=meta_suggestion,
        critique=critique,
    )
    out_dir = _data_dir() / "runs" / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "prompt.txt").write_text(prompt)
    (out_dir / "response.json").write_text(json.dumps({
        "research_suggestion": research_suggestion,
        "meta_suggestion": meta_suggestion,
        "critique": critique,
    }, indent=2))
    (out_dir / "meta.json").write_text(record.model_dump_json(indent=2))
    return record


def load_runs(dataset_path: str | None = None) -> list[RunRecord]:
    runs_dir = _data_dir() / "runs"
    if not runs_dir.exists():
        return []
    records = []
    for d in sorted(runs_dir.iterdir()):
        meta = d / "meta.json"
        if not meta.exists():
            continue
        r = RunRecord.model_validate_json(meta.read_text())
        if dataset_path is None or r.dataset_path == str(Path(dataset_path).expanduser()):
            records.append(r)
    return records
```

### 3.5 `engine.py` (target)

```python
"""ResearchEngine — MVP one-shot suggest; Phase 2 wires run(); Phase 3 wires recurse()."""

from __future__ import annotations
import json
import litellm
from pydantic import BaseModel

from .dataset import Dataset
from .goal import Goal, StructuredGoal
from .memory import RunRecord, save_run


SYSTEM_PROMPT = """You are an auto-research planner. Given a dataset description and a
research goal, you propose:
  1. research_suggestion — the single most informative first experiment to run.
     Be specific: name features, target, evaluation.
  2. meta_suggestion — what you would change about THIS PROMPT or YOUR APPROACH
     to give a better suggestion next time. This is the recursive seed.

Respond as JSON: {"research_suggestion": "...", "meta_suggestion": "..."}"""


CRITIQUE_PROMPT = """You are a research critic. Given a research suggestion, identify
the strongest objection or risk. Be specific. Respond as JSON: {"critique": "..."}"""


class SuggestResult(BaseModel):
    research_suggestion: str
    meta_suggestion: str
    critique: str | None = None
    run_id: str


class Engine:
    def __init__(
        self,
        dataset: Dataset,
        goal: Goal,
        *,
        model: str = "anthropic/claude-sonnet-4-6",
    ) -> None:
        self.dataset = dataset
        self.goal = goal
        self.model = model

    def _goal_text(self) -> str:
        if isinstance(self.goal, StructuredGoal):
            return self.goal.model_dump_json()
        return self.goal

    def _dataset_summary(self) -> str:
        names = self.dataset.list()
        lines = [f"Dataset rooted at: {self.dataset.path}", "Available tables:"]
        for n in names:
            try:
                cols = self.dataset.columns(n)
                lines.append(f"  - {n}: {len(cols)} cols ({', '.join(cols[:8])}{'...' if len(cols) > 8 else ''})")
            except Exception as e:
                lines.append(f"  - {n}: (could not introspect — {e})")
        return "\n".join(lines)

    def _build_prompt(self) -> str:
        return f"{self._dataset_summary()}\n\nResearch goal:\n{self._goal_text()}"

    def suggest(self, *, critique: bool = False) -> SuggestResult:
        prompt = self._build_prompt()
        response = litellm.completion(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
        )
        parsed = json.loads(response.choices[0].message.content)
        research = parsed["research_suggestion"]
        meta = parsed["meta_suggestion"]

        critique_text: str | None = None
        if critique:
            crit_resp = litellm.completion(
                model=self.model,
                messages=[
                    {"role": "system", "content": CRITIQUE_PROMPT},
                    {"role": "user", "content": research},
                ],
                response_format={"type": "json_object"},
            )
            critique_text = json.loads(crit_resp.choices[0].message.content)["critique"]

        record = save_run(
            dataset_path=str(self.dataset.path),
            goal=self._goal_text(),
            model=self.model,
            prompt=prompt,
            research_suggestion=research,
            meta_suggestion=meta,
            critique=critique_text,
        )
        return SuggestResult(
            research_suggestion=research,
            meta_suggestion=meta,
            critique=critique_text,
            run_id=record.run_id,
        )

    def history(self) -> list[RunRecord]:
        from .memory import load_runs
        return load_runs(str(self.dataset.path))

    def run(self):
        raise NotImplementedError(
            "Engine.run() — full iterative loop — lands in Phase 2."
        )

    def recurse(self):
        raise NotImplementedError(
            "Engine.recurse() — the recursive auto-improve move — lands in Phase 3. "
            "Reads accumulated runs + meta_suggestions and mutates own prompt/policy."
        )
```

### 3.6 `cli.py` (target)

```python
"""maunakea CLI."""

from __future__ import annotations
import click
from . import __version__
from .dataset import Dataset
from .engine import Engine


@click.group()
@click.version_option(__version__, prog_name="maunakea")
def main() -> None:
    """Generic recursive auto-improve system."""


@main.command()
@click.option("--dataset", "dataset_path", required=True, type=click.Path(exists=True))
@click.option("--goal", "goal_text", required=True, type=str)
@click.option("--model", default="anthropic/claude-sonnet-4-6", show_default=True)
@click.option("--critique", is_flag=True, help="Add a Challenger pass (second LLM call).")
def suggest(dataset_path: str, goal_text: str, model: str, critique: bool) -> None:
    """Propose a research step + a self-improvement suggestion."""
    ds = Dataset(dataset_path)
    engine = Engine(ds, goal_text, model=model)
    result = engine.suggest(critique=critique)
    click.echo(f"[Run {result.run_id} — saved]\n")
    click.echo(f"Research suggestion:\n  {result.research_suggestion}\n")
    click.echo(f"Meta-suggestion (for next run):\n  {result.meta_suggestion}")
    if result.critique:
        click.echo(f"\nCritique:\n  {result.critique}")


@main.command()
@click.option("--dataset", "dataset_path", required=True, type=click.Path(exists=True))
def history(dataset_path: str) -> None:
    """List past runs for this dataset."""
    ds = Dataset(dataset_path)
    runs = Engine(ds, "_history_only_").history()
    if not runs:
        click.echo("[no prior runs against this dataset]")
        return
    click.echo(f"[{len(runs)} run(s) found]")
    for r in runs:
        click.echo(f"  {r.run_id}  {r.timestamp}  goal=\"{r.goal[:60]}\"")


if __name__ == "__main__":
    main()
```

---

## 4. Tests + CI decoupling check

### 4.1 Tests

```python
# tests/conftest.py
from pathlib import Path
import pytest


@pytest.fixture
def rainier_cache() -> Path:
    p = Path.home() / "projects" / "rainier" / "data" / "cache"
    if not p.exists():
        pytest.skip(f"rainier cache not at {p}")
    return p


@pytest.fixture
def mock_litellm(mocker):
    """Stub litellm.completion with structured JSON output."""
    def fake_completion(messages, response_format=None, **kwargs):
        system = messages[0]["content"]
        if "research_suggestion" in system:
            content = '{"research_suggestion": "run OLS of fwd_30d_ret on rank_5/10/20", "meta_suggestion": "add VIX regime context"}'
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
```

```python
# tests/test_dataset.py
from maunakea import Dataset

def test_list_against_rainier(rainier_cache):
    ds = Dataset(rainier_cache)
    names = ds.list()
    for req in ("thematic_features_daily", "thematic_labels_daily", "thematic_universe", "macro_context"):
        assert req in names

def test_load_thematic_features(rainier_cache):
    ds = Dataset(rainier_cache)
    df = ds.load("thematic_features_daily")
    assert len(df) > 0
    assert "symbol" in df.columns and "asof_date" in df.columns
```

```python
# tests/test_engine.py
from maunakea import Dataset, Engine

def test_suggest_returns_both_fields(rainier_cache, mock_litellm):
    ds = Dataset(rainier_cache)
    e = Engine(ds, "predict 30-day forward returns")
    r = e.suggest()
    assert r.research_suggestion and r.meta_suggestion
    assert r.critique is None
    assert r.run_id

def test_suggest_with_critique(rainier_cache, mock_litellm):
    ds = Dataset(rainier_cache)
    e = Engine(ds, "x")
    r = e.suggest(critique=True)
    assert r.critique is not None
    assert mock_litellm.call_count == 2

def test_run_raises(rainier_cache):
    import pytest
    from maunakea import Dataset, Engine
    e = Engine(Dataset(rainier_cache), "x")
    with pytest.raises(NotImplementedError):
        e.run()
    with pytest.raises(NotImplementedError):
        e.recurse()
```

```python
# tests/test_memory.py
from maunakea import Dataset, Engine

def test_suggest_persists_run(rainier_cache, mock_litellm, tmp_data_dir):
    ds = Dataset(rainier_cache)
    e = Engine(ds, "x")
    r = e.suggest()
    run_dir = tmp_data_dir / "runs" / r.run_id
    assert (run_dir / "prompt.txt").exists()
    assert (run_dir / "response.json").exists()
    assert (run_dir / "meta.json").exists()

def test_history_reads_past_runs(rainier_cache, mock_litellm):
    ds = Dataset(rainier_cache)
    e = Engine(ds, "x")
    r = e.suggest()
    past = e.history()
    assert any(rec.run_id == r.run_id for rec in past)
```

```python
# tests/test_smoke.py
import subprocess, sys

def test_cli_version():
    out = subprocess.check_output([sys.executable, "-m", "maunakea.cli", "--version"], text=True)
    assert "0.0.1" in out

def test_no_rainier_import_in_src():
    """Decoupling invariant: zero references to rainier in src/maunakea/."""
    result = subprocess.run(
        ["rg", "-l", "rainier", "src/maunakea/"],
        capture_output=True, text=True,
    )
    assert result.returncode == 1, f"unexpected rainier refs: {result.stdout}"
```

### 4.2 CI decoupling step

`.github/workflows/ci.yml` adds a fourth step alongside build / ruff / pytest:

```yaml
- name: Decoupling check (no rainier imports in src/maunakea/)
  run: |
    if rg -l "rainier" src/maunakea/; then
      echo "FAIL: src/maunakea/ contains references to rainier"
      exit 1
    fi
```

Load-bearing invariant. CI fails on any accidental coupling.

---

## 5. Non-goals (explicit)

- **No** `Engine.run()` or `Engine.recurse()` implementation. Both raise `NotImplementedError`.
- **No** structured-goal code path. `StructuredGoal` shell declared; only NL branch runs.
- **No** editable install of rainier. A4 enforces this.
- **No** homegrown LLM provider abstraction. `litellm` direct.
- **No** CSV / SQL / cloud Dataset adapters. Parquet only.
- **No** cost tracking, budget caps, scorer. All Phase 2.
- **No** subcommands beyond `--version` / `--help` / `suggest` / `history`.
- **No** trading-specific code (`picks` / `track` / `backtest`). Those live in rainier as Phase 4 follow-up.
- **No** branch protection setup. Worker creates the repo + pushes initial commit to `main`. Operator adds rules afterward.
- **No** modifications to rainier in this task.

---

## 6. Dependencies

- `litellm` resolves to a version with Anthropic support.
- `gh` CLI authenticated as `edisonshen`.
- Rainier-produced parquets at `~/projects/rainier/data/cache/` (verified 2026-05-23).
- API key in env IF the worker wants a live dogfood at the end (optional — A1–A12 all pass with mocked LLM).

---

## 7. Bootstrap exception

Per global CLAUDE.md §6, subagents never push to `main`. For a brand-new repo, there is no `main` to violate. The worker's first push to `origin/main` IS the bootstrap; documented one-time exception. From PR #2 onward, normal discipline applies.

Worker MUST surface in return message:

> "First commit: bootstrap-direct-to-main (no PR — repo did not exist). All future commits go through PR-against-main per CLAUDE.md §6."

---

## 8. Return contract

```
GH repo URL: <https url>
visibility: public
license: MIT
initial commit SHA: <sha>
CI run URL: <url>
final CI gate: PASS | FAIL
codex iterations: <N>  (0 if SKIPPED — bootstrap allowed to skip codex; /review mandatory)
/review invocations: <M>
files created: <count>
tests added: <count + names>
acceptance: A1=PASS A2=PASS A3=PASS A4=PASS A5=PASS A6=PASS A7=PASS A8=PASS A9=PASS A10=PASS A11=PASS A12=PASS
decoupling check (rg "rainier" src/maunakea/): clean | DIRTY (<matches>)
dogfood: did | skipped — <real LLM output one-liner if did, else "no API key">
WIP file: deleted | preserved at <path>
notes: <anything operator should know>
```

If any A# fails, worker returns **BLOCKED** with WIP preserved and the specific failure named.

---

## 9. Inherited decisions

- Repo name `maunakea`; fresh git history; tooling parity with rainier (uv + ruff + pytest + GH Actions).
- **PUBLIC repo, MIT license.**
- Maunakea is a **generic recursive auto-improve system**, not a research framework. Zero rainier dep (CI-enforced).
- Port-and-generalize from rainier's research code in Phase 2 (not Phase 1).
- NL goal for MVP; typed `Union[str, StructuredGoal]` for forward-compat.
- Rainier is first dogfood user. `~/projects/rainier/data/cache/` is the test fixture path.
- `litellm` for LLM backend; structured JSON output.
- Phase 1 = end-to-end MVP with persistence + meta_suggestion + critique flag. Not strict skeleton.
- Three-layer mental model (LLM + framework + harness); thin-harness principle.
- Trading wrapper lives in rainier (Phase 4), not maunakea.
- README + ARCHITECTURE.md are external-facing artifacts (people arriving via fengshen.dev/recursive).

---

## 10. Approval

| Step | State |
|---|---|
| Drafted | 2026-05-23 by coord `c02eab1f` (v5) |
| Approved | 2026-05-23 by operator ("yes." to proceed with rewrite + dispatch plan) |
| Dispatched | _pending — operator confirms final task plan before coord launches worker_ |
