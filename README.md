# maunakea

> Generic recursive auto-improve system. Give it a dataset and a goal — it explores,
> remembers, and gets better.

You hand `maunakea` a folder of parquet files and a research question in natural
language. It calls an LLM and proposes the next experiment to run. It *also*
proposes what to change about its own approach for next time. Both outputs persist.
Over many runs, the accumulated memory and self-improvement suggestions feed back
into the system, so the system gets better at research — that's the recursive part.

The first dogfood user is [`rainier`](https://github.com/edisonshen/rainier) (QU100
trading data). But maunakea itself is **domain-agnostic**: anyone with a dataset and
a "help me find what's in this" problem can point it at their files.

This project sits in the conversation that the [Recursive Superintelligence lab](https://fengshen.dev/recursive/)
is having about how to build systems that improve themselves.

## Status

- **v0.0.1 — Phase 1 MVP.** One LLM call per `suggest()` returns both a research
  suggestion AND a self-improvement suggestion. Persistence lands. Iterative search
  (`Engine.run()`) and the recursive move (`Engine.recurse()`) are scaffolded as
  `NotImplementedError` for Phase 2 / Phase 3.

## Install

```bash
git clone https://github.com/edisonshen/maunakea.git
cd maunakea
uv sync --extra dev
```

Requires Python 3.11+ and an API key in env for whichever model you target (defaults
to `anthropic/claude-sonnet-4-6` via [`litellm`](https://github.com/BerriAI/litellm)).

## Usage

```bash
$ maunakea suggest \
    --dataset ~/projects/rainier/data/cache/ \
    --goal "find features that predict 30-day forward returns"

[Run 20260523-184213-a1b2c3 — saved]

Research suggestion:
  Compute rank correlation between rank_5/rank_10/rank_20 and fwd_30d_ret.
  Group by sector; look for sectors where rank_5 dominates rank_20.

Meta-suggestion (for next run):
  Add macro_context.vix to the prompt context so the next suggestion can be
  regime-conditional.

$ maunakea history --dataset ~/projects/rainier/data/cache/
[1 run(s) found]
  20260523-184213-a1b2c3  2026-05-23T18:42:13+00:00  goal="find features that..."
```

Add `--critique` to trigger a second LLM call that returns the strongest objection
to the proposed suggestion.

Runs persist to `~/projects/maunakea/data/runs/<run_id>/` as `prompt.txt`,
`response.json`, `meta.json`. Override the root with `MAUNAKEA_DATA_DIR`.

## Architecture

Three layers (see [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for full detail):

```
LLM        ← replaceable (anything litellm wraps)
Harness    ← thin glue: prompt build + JSON parse (~50 LOC)
Framework  ← memory, persistence, history, recursion machinery
```

Public API:

```python
from maunakea import Dataset, Engine

ds = Dataset("~/projects/rainier/data/cache/")
e  = Engine(ds, "predict 30-day forward returns")

result = e.suggest()                # one LLM call → both suggestions
result.research_suggestion          # the next experiment
result.meta_suggestion              # what to change about the approach
result.run_id                       # saved under data/runs/<run_id>/

past = e.history()                  # list[RunRecord]

e.run()       # NotImplementedError — Phase 2
e.recurse()   # NotImplementedError — Phase 3
```

## Prior art

Maunakea sits in a conversation. The most directly applicable prior work:

- **Promptbreeder** (Rocktäschel et al., ICML 2024) — self-referential prompt
  evolution. Direct ancestor of `Engine.recurse()`.
- **AlphaEvolve** (DeepMind, 2025) — evolutionary search over programs with LLM
  mutations. Architecture model for Phase 2's `run()`.
- **OpenEvolve** — open-source AlphaEvolve reimplementation; the [Recursive
  Superintelligence lab](https://fengshen.dev/recursive/) calls this its "primary
  fork target for applicants."
- **AI Scientist** (Sakana) — end-to-end ideation → code → experiment → write loops.
  Informs Phase 2 output format.
- **SWE-agent / Live-SWE-agent** — self-improving coding agents (77.4% SWE-bench).
  Architecture model for Phase 3's `recurse()`.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) §2 for the full reading list and
the four-pillar mapping.

## Decoupling invariant

maunakea has **zero** runtime or import dependency on any specific downstream user
(including rainier). CI enforces this on every push:

```bash
rg "rainier" src/maunakea/    # MUST return zero matches
```

Trading-specific behaviour lives in the rainier repo as a thin wrapper; bio-specific
behaviour would live in a bio repo. Maunakea stays generic.

## License

MIT. See [LICENSE](LICENSE).
