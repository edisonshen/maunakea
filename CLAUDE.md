# maunakea — Claude Code working notes

You're likely Claude Code working in this repo. Read these before touching anything.

## What this is

Maunakea is a **generic recursive auto-improve system (RAIS)**. Inputs: a dataset
path and a research goal. Output: a research suggestion plus a self-improvement
suggestion, persisted to disk. Over many runs, the accumulated memory and meta-
suggestions feed back into the system so it gets better at research — that's the
recursive part.

Maunakea is **domain-agnostic**. The first dogfood user is `rainier` (trading data),
but maunakea itself MUST NOT import or reference rainier.

## Decoupling invariant (load-bearing)

```bash
rg "rainier" src/maunakea/
```

MUST return zero matches. CI enforces this on every push and PR. If you need
trading-specific behaviour, put it in a downstream wrapper repo — never here.

## Source of truth

- **Design:** [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — three-layer model,
  pillar mapping, phase roadmap.
- **External framing:** [`README.md`](README.md) — install + prior art + link to
  [fengshen.dev/recursive](https://fengshen.dev/recursive/).
- **Phase 1 plan (origin):** lives in the rainier repo at
  `docs/TASK-PLAN-maunakea-skeleton.md`.

## Three layers

```
┌─────────────────────────────────────────────────┐
│  LLM        ← replaceable (anything litellm wraps)
├─────────────────────────────────────────────────┤
│  Harness    ← thin glue: build prompt, parse JSON
│              (~50 LOC; shrinks as models improve)
├─────────────────────────────────────────────────┤
│  Framework  ← memory, persistence, history,
│              recursion machinery. The durable thing.
└─────────────────────────────────────────────────┘
```

**Thin-harness principle.** Don't build harness pieces today's models will obsolete
in a year. Build framework pieces (memory, budgets, recursion) that today's and
tomorrow's models both need.

## Phases

| Phase | What's in | Status |
|---|---|---|
| **1 — MVP** | `Engine.suggest()` (recursive seed) + `history()` + Dataset/Goal/memory | this PR |
| **2 — iterate** | `Engine.run()` iterative loop, pluggable scorer, cost cap | NIE today |
| **3 — recurse** | `Engine.recurse()` — read memory, mutate own prompt/policy | NIE today |
| **4 — apps** | downstream wrappers (rainier trading, bio, ad-tech) | downstream |

`Engine.run()` and `Engine.recurse()` raise `NotImplementedError` in Phase 1.

## House style

- Terse commits. `fix(memory): persist critique field`.
- Tests come with the feature, not after. Run `uv run pytest -q` before pushing.
- No premature abstractions. No homegrown LLM provider abstraction — `litellm` direct.
- Filesystem state must survive crashes (atomic writes when applicable).
- Single CLI: `maunakea suggest` + `maunakea history`. Don't add subcommands without
  a design conversation.

## What to work on next

After v0.0.1 lands (this PR), Phase 2 priorities (operator-driven, not auto-dispatched):

1. **Engine.run() iterative loop** — bandit-style search; pluggable scorer (LLM-as-judge
   default); `cost_pilot` budget cap.
2. **Memory queries** — index by dataset + goal; surface meta_suggestions to next run.
3. **Phase 3 sketch** — `Engine.recurse()` design doc that consumes accumulated
   meta_suggestions and mutates the prompt template.
