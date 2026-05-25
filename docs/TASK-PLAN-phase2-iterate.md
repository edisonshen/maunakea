# TASK PLAN: maunakea Phase 2 — iterative `Engine.run()`

- **Parent design:** [DESIGN-split-research-to-maunakea.md](https://github.com/edisonshen/rainier/blob/main/docs/DESIGN-split-research-to-maunakea.md) §5 Phase 2 (in rainier docs — the decision archive)
- **Phase 1 genealogy:** [TASK-PLAN-maunakea-skeleton.md](TASK-PLAN-maunakea-skeleton.md)
- **Slug:** `phase2-iterate`
- **Priority:** P1 (queued; dispatch on operator green light)
- **Owner:** TBD (dispatched subagent when approved)
- **Status:** Drafted; awaiting operator approval to dispatch
- **Date:** 2026-05-24

---

## 1. Goal

Wire up `Engine.run()` — the **iterative research loop** that's the headline Phase 2 deliverable. Inputs: a `Dataset` + `Goal` + a budget. Outputs: a `ResearchResult` containing ranked hypotheses with scores, after iterative exploration capped by cost.

This phase ports the four framework building blocks from rainier (`bandit/`, `evaluator/`, `rewards/`, `cost_pilot.py`, `survivorship.py`), wraps them in a generic Scorer protocol, and orchestrates them inside `Engine.run()`. After Phase 2 lands, maunakea is no longer a one-shot suggestion tool — it's a real research agent that explores hypothesis space within a budget.

**Pillar coverage this phase nails down (mapping to Tian's RSI framework):**

- **Pillar 3 (better search)** — bandit / MAP-Elites style exploration over hypothesis space.
- **Pillar 4 (economic scaling)** — `cost_pilot` enforces token budgets; `--budget` CLI flag.
- **Pillar 2 (memory)** — Phase 1's `RunRecord` extended to capture full `RunResult` (multiple hypotheses + scores per run).
- **Pillar 1 (Solver↔Challenger)** — partially: the LLM-as-judge scorer is a baby Challenger that critiques each candidate hypothesis. Full self-play still waits for Phase 3.

`Engine.recurse()` stays `NotImplementedError` — that's Phase 3.

---

## 2. Acceptance criteria

| # | Criterion | Verification |
|---|---|---|
| B1 | `src/maunakea/bandit/`, `evaluator/`, `rewards/` exist with passing tests | `pytest tests/bandit/ tests/evaluator/ tests/rewards/` |
| B2 | `src/maunakea/cost_pilot.py`, `survivorship.py` exist with passing tests | `pytest tests/test_cost_pilot.py tests/test_survivorship.py` |
| B3 | `src/maunakea/scorer.py` defines a `Scorer` Protocol with `LLMJudgeScorer` as default impl | inspect file |
| B4 | `Engine.run(budget: float) -> ResearchResult` returns a non-empty `ResearchResult` end-to-end | integration test |
| B5 | `ResearchResult` is a Pydantic model with `hypotheses: list[ScoredHypothesis]`, `cost_used: float`, `runs_executed: int`, `meta_suggestion: str` | inspect schema |
| B6 | `maunakea run --dataset <PATH> --goal "<NL>" --budget 0.50` CLI exits 0, prints findings, persists `RunResult` | smoke test |
| B7 | **Decoupling preserved:** `rg "rainier" src/maunakea/` still returns zero matches. CI step still passes. | grep + CI |
| B8 | Integration test: `Engine.run(budget=0.50)` against rainier's parquet cache produces a non-empty result within $0.50 token spend (mocked LLM in CI; live LLM in optional dogfood) | integration test |
| B9 | Cost tracking accurate: `cost_used` field matches sum of `litellm` reported tokens × model rate within 1% | unit test |
| B10 | `Engine.recurse()` still raises `NotImplementedError` with updated docstring pointing at Phase 3 | inspect |
| B11 | CI green: build + ruff + pytest + decoupling-grep (4 jobs from Phase 1, no new jobs needed) | `gh run list` |
| B12 | Updated `README.md` shows the Phase 2 CLI example; `docs/ARCHITECTURE.md` updated phase roadmap to mark Phase 2 done | inspect |

---

## 3. Files to create

```
src/maunakea/
├── bandit/                  # ← ported from src/rainier/research/bandit/
│   ├── __init__.py
│   └── <files preserved from rainier>
├── evaluator/               # ← ported from src/rainier/research/evaluator/
│   ├── __init__.py
│   └── <files preserved from rainier>
├── rewards/                 # ← ported from src/rainier/research/rewards/
│   ├── __init__.py
│   └── <files preserved from rainier>
├── cost_pilot.py            # ← ported from src/rainier/research/cost_pilot.py
├── survivorship.py          # ← ported from src/rainier/research/survivorship.py
├── scorer.py                # NEW — Scorer Protocol + LLMJudgeScorer default
└── result.py                # NEW — ResearchResult, ScoredHypothesis Pydantic models

tests/
├── bandit/
├── evaluator/
├── rewards/
├── test_cost_pilot.py
├── test_survivorship.py
├── test_scorer.py
├── test_run_integration.py  # NEW — full Engine.run() against rainier cache w/ mocked LLM
```

## 4. Files to modify

- `src/maunakea/engine.py` — implement `Engine.run()` using ported building blocks. `Engine.recurse()` docstring updated to "Phase 3" with rationale.
- `src/maunakea/cli.py` — add `run` subcommand with `--budget` flag.
- `src/maunakea/__init__.py` — re-export `ResearchResult`, `ScoredHypothesis`, `Scorer`, `LLMJudgeScorer`.
- `src/maunakea/memory.py` — extend `RunRecord` to handle `RunResult` (multi-hypothesis runs) alongside the existing single-suggestion records.
- `pyproject.toml` — add any deps the ported modules need (numpy, scipy if bandit uses them; verify by inspection during port).
- `README.md` — add Phase 2 CLI example + roadmap update.
- `docs/ARCHITECTURE.md` — mark Phase 2 done; lift Phase 3 to "next."

---

## 5. Port-and-generalize approach (per design doc Phase 2 strategy)

For each rainier module being ported:

1. **Copy verbatim first.** `cp -r src/rainier/research/<module>/ src/maunakea/<module>/` (or `git mv` equivalent in the maunakea worktree — but maunakea doesn't have rainier's git history; treat it as plain copy then commit).
2. **Strip rainier-specific assumptions.** Any references to rainier's data layer, types, config — replace with maunakea's generic primitives.
3. **Re-test.** Copy the corresponding `tests/research/<module>/` tests; update imports; verify they pass under maunakea.
4. **Decoupling check.** `rg "rainier" src/maunakea/<module>/` returns zero.
5. If a module resists generalization (genuinely depends on rainier-specific knowledge that can't be lifted out), **rewrite that module from scratch** using the design docs as reference — don't drag rainier baggage into maunakea. Note the rewrite in the PR description.

The port is NOT a behavior-preserving move (that was Phase R). It's a **port-and-generalize**: the resulting code in maunakea may behave differently because it operates on a generic `Dataset`/`Goal` instead of rainier-specific types. That's expected. Test against the new generic API; don't try to byte-match rainier's old behavior.

---

## 6. Engine.run() shape (target)

```python
def run(
    self,
    *,
    budget: float = 1.0,
    max_iterations: int = 20,
    scorer: Scorer | None = None,
) -> ResearchResult:
    """Iterative research loop.

    Uses bandit-style search to explore hypothesis space within `budget`
    (USD of LLM tokens). Each iteration:
      1. Bandit picks a region of hypothesis space to explore.
      2. LLM proposes a hypothesis in that region.
      3. Scorer scores the hypothesis (LLM-as-judge by default).
      4. Reward signal updates bandit.
      5. Cost_pilot deducts spend; if budget exhausted, stop.

    Returns a ResearchResult with ranked hypotheses, full cost trace, and
    a meta_suggestion for what to change about run() next time (recursive seed
    continues from Phase 1).
    """
```

---

## 7. Coordination with rainier-side cleanup

Phase 2's port happens entirely in maunakea. **The rainier-side cleanup (delete `src/rainier/research/{bandit,evaluator,rewards,providers}/`, `cost_pilot.py`, `survivorship.py` from rainier) is a SEPARATE PR in rainier** dispatched AFTER maunakea Phase 2 lands.

Sequencing:
1. Maunakea Phase 2 PR(s) — port + Engine.run() + integration test. Merges first.
2. Rainier cleanup PR — deletes the ported modules + research/cli.py + research/__init__.py. Verifies rainier production pipeline still works (no rainier production code imports the deleted modules; verify by grep before deletion).
3. Both repos in sync.

Do NOT delete from rainier in this Phase 2 task. That's a follow-up.

---

## 8. Non-goals (explicit)

- **No** `Engine.recurse()` implementation. Phase 3.
- **No** skill extraction / skill store. Phase 3.
- **No** structured-goal code paths beyond what Phase 1 already declared.
- **No** trading wrapper (`picks` / `track` / `backtest`). Phase 4, rainier-side.
- **No** changes to Phase 1's `Engine.suggest()` API or behavior.
- **No** breaking changes to the existing `RunRecord` schema. `RunResult` is additive.
- **No** rainier-side modifications in this task. Cleanup is a separate follow-up.
- **No** new LLM provider abstraction. `litellm` direct, same as Phase 1.
- **No** persistence schema migration. New `RunResult` lives alongside `RunRecord`.
- **No** Pillar 1 full self-play. The LLM-as-judge scorer is the minimum slice that touches Pillar 1; Solver↔Challenger proper is Phase 3.

---

## 9. Risks + mitigations

| Risk | Mitigation |
|---|---|
| Ported module has hidden rainier dep that defeats decoupling check | Per-file grep before each port commit; CI decoupling check is load-bearing. |
| `Engine.run()` cost overruns budget due to bandit exploring too aggressively | `cost_pilot` checks remaining budget before each LLM call; refuse to call if would exceed; return partial result with `cost_used` < `budget` and `truncated=True` flag. |
| Generalization changes behavior in ways the operator doesn't expect | Integration test against rainier's data with mocked LLM is the contract. Behavior under real LLM is exploratory — that's the point. |
| Phase 2 PR becomes too large to review | Acceptable to split into sub-PRs per module (e.g., bandit port PR, evaluator port PR, then "wire Engine.run()" PR). Worker decides the breakdown. |
| Rainier production accidentally breaks if it secretly imports a ported module | Phase 2 does NOT delete from rainier. Rainier-side cleanup PR explicitly greps before deletion. |
| Cost spike during integration test dogfood | Integration test uses mocked LLM in CI ($0). Live dogfood is opt-in via API key in env; capped at $0.50. |

---

## 10. Dispatch checklist (operator's gate before this fires)

Operator confirms before this task is dispatched:

- [ ] Phase 1 has been operator-dogfooded at least once (so we know `suggest()` works for real, not just for tests).
- [ ] Operator has reviewed Phase 1's persisted `RunRecord`s and is happy with the schema before we extend it.
- [ ] No rainier-side production breakage from Phase R rename merge (PR #83) — verified by ~1 week of continued daily pipeline running clean.
- [ ] Budget OK for integration test ($0.50 mocked in CI; live dogfood operator's call).

When all four are yes, this task is ready to dispatch. Worker brief inlines this whole doc + the global Subagent Dispatch Contract.

---

## 11. Approval

| Step | State |
|---|---|
| Drafted | 2026-05-24 by coord `c02eab1f` |
| Approved | _pending — operator reviews + signs off when ready_ |
| Dispatched | _pending_ |
