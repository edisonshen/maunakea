# Architecture

Maunakea is a generic recursive auto-improve system. This document describes the
three-layer mental model the codebase is organised around, the public API surface,
the persistence shape, and the phase roadmap.

---

## 1. Three layers

```
┌─────────────────────────────────────────────────┐
│  LLM         ← replaceable (Anthropic, OpenAI,  │
│               DeepSeek, anything litellm wraps) │
├─────────────────────────────────────────────────┤
│  Harness     ← thin glue: format the dataset    │
│               into prompt text, parse structured│
│               JSON back. ~50 LOC in MVP.        │
├─────────────────────────────────────────────────┤
│  Framework   ← memory, persistence, history,    │
│               skill store, recursion machinery. │
│               The durable thing maunakea IS.    │
└─────────────────────────────────────────────────┘
```

**Thin-harness principle.** As LLMs get smarter, the harness shrinks. Today the
harness builds a "here is the dataset schema, here is the goal" prompt; tomorrow
the LLM might do that itself with a generic tool-use interface. Don't build harness
pieces that next year's model will obsolete. *Build framework pieces that today's
and next year's model both need* — memory across sessions, budget enforcement,
recursion machinery. Models can't do those for you no matter how smart they get.

---

## 2. Prior art / reading list

The most directly applicable prior work, in priority order:

| Source | Why it matters |
|---|---|
| **Promptbreeder** (Rocktäschel, ICML 2024) | Self-referential self-improvement via prompt evolution. Direct ancestor of `Engine.recurse()`. Read before Phase 3. |
| **"Open-Endedness is Essential for ASI"** (Rocktäschel et al., ICML 2024) | Position paper. Philosophical backing for the whole RSI direction. |
| **Recursive Superintelligence lab** (founded late 2025) — [fengshen.dev/recursive](https://fengshen.dev/recursive/) | The lab maunakea aspires to be in conversation with. Tian's four-pillar RSI framework. |
| **AlphaEvolve** (DeepMind 2025) | First "Level 1" recursive system — evolutionary search over programs with LLM mutations. Architecture model for Phase 2's `run()`. |
| **OpenEvolve** | Open-source AlphaEvolve reimplementation. Primary fork target for the RS lab applicant pool. |
| **AI Scientist** (Sakana) | End-to-end ideation → code → experiment → write loops. Informs Phase 2 output format. |
| **SWE-agent / Live-SWE-agent** | Self-improving coding agents (77.4% SWE-bench). Architecture model for Phase 3's `recurse()`. |
| **POET / Enhanced POET** (Rocktäschel et al.) | Co-evolves environments + agents. Instructive even at fixed-dataset MVP scope — the search space IS the harness. |
| **MAP-Elites** | Quality-diversity algorithm. Foundational to the bandit-style search planned for Phase 2. |
| **OMNI / OMNI-EPIC** | Open-endedness frameworks. Adjacent. |

### 2.1 Four-pillar RSI mapping

Tian's [four-pillar RSI framework](https://fengshen.dev/recursive/) maps to
maunakea components as follows:

| Pillar | Maunakea component | Phase |
|---|---|---|
| **Synthetic data via Solver↔Challenger** | `Engine.suggest(critique=True)` (light) → full self-play `run()` | 1 → 2 |
| **Memory & continuous learning** | `memory.py` RunRecord; `history()` reads accumulated runs | 1 |
| **Better search via learned action-space** | `Engine.run()` bandit + MAP-Elites search | 2 |
| **Economic scaling** | `cost_pilot` budget cap in Phase 2 | 2 |
| **Self-modification of the search policy** | `Engine.recurse()` mutates own prompt/policy from accumulated meta-suggestions | 3 |

---

## 3. Public API

```python
from maunakea import Dataset, Goal, Engine, StructuredGoal

ds = Dataset("~/projects/rainier/data/cache/")
g  = Goal("find features predicting 30-day forward returns")   # str | StructuredGoal
e  = Engine(ds, g, model="anthropic/claude-sonnet-4-6")

result = e.suggest(critique=False)
# result.research_suggestion   — next experiment to run
# result.meta_suggestion       — what to change about the approach (recursive seed)
# result.critique              — None unless critique=True
# result.run_id                — persisted to data/runs/<run_id>/

past = e.history()             # list[RunRecord]; filtered by ds.path

e.run()       # NotImplementedError — Phase 2
e.recurse()   # NotImplementedError — Phase 3
```

### 3.1 Dataset

```python
ds.list()                                   # ["thematic_features_daily", ...]
ds.columns("thematic_features_daily")       # ["symbol", "asof_date", ...]
ds.sample("thematic_features_daily", n=10)
ds.load("thematic_features_daily")          # pd.DataFrame
```

MVP: parquet only (single file or directory of files). CSV / SQL / cloud adapters
land if/when needed.

### 3.2 Goal

```python
g = Goal("find features predicting 30-day forward returns")        # MVP path

g = StructuredGoal(target="fwd_30d_ret", features=["rank_*"], horizon=30)
# declared shell; only the str branch runs in MVP code paths.
```

### 3.3 Engine

`Engine.suggest()` makes **one** `litellm.completion` call with
`response_format={"type": "json_object"}`. The structured response carries BOTH
`research_suggestion` and `meta_suggestion`. That's the recursive seed in a single
round-trip.

`Engine.suggest(critique=True)` triggers a **second** call against a separate
Challenger system prompt. Lightweight Solver↔Challenger pattern; full self-play
arrives with Phase 2's `run()`.

---

## 4. Persistence

Every `suggest()` writes to:

```
$MAUNAKEA_DATA_DIR/runs/<run_id>/
  ├── prompt.txt        # exact prompt sent to the model
  ├── response.json     # parsed research_suggestion + meta_suggestion + critique
  └── meta.json         # RunRecord (timestamp, dataset_path, goal, model)
```

`<run_id>` is `YYYYMMDD-HHMMSS-<6 hex>`. The data root defaults to
`~/projects/maunakea/data/` and is overridable via the `MAUNAKEA_DATA_DIR`
environment variable.

`Engine.history()` reads all `meta.json` files under `runs/` and filters by the
current `Dataset.path`. Phase 3 will index by `(dataset, goal)` and surface the
accumulated `meta_suggestion`s back into the prompt to close the recursion loop.

---

## 5. Phase roadmap

| Phase | What lands | When |
|---|---|---|
| **1 — MVP** | `Engine.suggest()` (recursive seed) + persistence + `history()` + CLI | v0.0.1 — this release |
| **2 — iterate** | `Engine.run()` iterative loop; pluggable scorer; cost_pilot budget; bandit/MAP-Elites search | next |
| **3 — recurse** | `Engine.recurse()` — reads accumulated meta_suggestions, mutates prompt/policy, backtests, promotes | after Phase 2 dogfood |
| **4 — apps** | downstream wrappers (rainier trading; bio / ad-tech if users show up) | downstream repos, not maunakea |

---

## 6. Decoupling invariant

```bash
rg "rainier" src/maunakea/    # MUST return zero matches
```

CI enforces this on every push and PR (`.github/workflows/ci.yml` ► `decoupling`
job). If you find yourself wanting to add a rainier-specific code path, file it as
a wrapper in the rainier repo and keep maunakea generic.
