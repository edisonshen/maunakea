"""Engine — MVP one-shot `suggest`; Phase 2 wires `run()`; Phase 3 wires `recurse()`.

Recursive seed: one `litellm.completion` call with structured JSON output
returns BOTH a `research_suggestion` and a `meta_suggestion`. The meta-
suggestion is what Phase 3's self-improvement loop will consume.

Flow:

    Dataset.list()/columns()  ─┐
                                ├──► build_prompt ──► litellm.completion
    goal (str | Structured)   ─┘                          │
                                                          ▼
                                              parse JSON → save_run
                                                          │
                                                          ▼
                                                   SuggestResult
"""

from __future__ import annotations

import json

import litellm
from pydantic import BaseModel

from .dataset import Dataset
from .goal import Goal, StructuredGoal
from .memory import RunRecord, load_runs, save_run


class EngineParseError(RuntimeError):
    """Raised when the LLM response isn't valid JSON or is missing required keys.

    Phase 3 depends on `meta_suggestion` being present on every persisted run.
    Failing loud at parse time beats writing a half-record the recursion loop
    would later choke on.
    """


class _ParsedSuggestion(BaseModel):
    research_suggestion: str
    meta_suggestion: str


class _ParsedCritique(BaseModel):
    critique: str


def _extract_content(response: object) -> str:
    try:
        content = response.choices[0].message.content  # type: ignore[attr-defined]
    except (AttributeError, IndexError) as e:
        raise EngineParseError(f"LLM response has no choices[0].message.content: {e!r}") from e
    if not isinstance(content, str) or not content.strip():
        raise EngineParseError("LLM returned empty / non-string content")
    return content


def _parse_suggestion(content: str) -> _ParsedSuggestion:
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as e:
        raise EngineParseError(f"LLM returned non-JSON content: {e!r} (raw: {content[:200]!r})") from e
    try:
        return _ParsedSuggestion.model_validate(payload)
    except Exception as e:
        raise EngineParseError(
            f"LLM JSON missing required fields (research_suggestion + meta_suggestion): {e!r}"
        ) from e


def _parse_critique(content: str) -> str:
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as e:
        raise EngineParseError(f"Critique returned non-JSON content: {e!r}") from e
    try:
        return _ParsedCritique.model_validate(payload).critique
    except Exception as e:
        raise EngineParseError(f"Critique JSON missing 'critique' field: {e!r}") from e

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
                preview = ", ".join(cols[:8])
                ellipsis = "..." if len(cols) > 8 else ""
                lines.append(f"  - {n}: {len(cols)} cols ({preview}{ellipsis})")
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
        parsed = _parse_suggestion(_extract_content(response))
        research = parsed.research_suggestion
        meta = parsed.meta_suggestion

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
            critique_text = _parse_critique(_extract_content(crit_resp))

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
        return load_runs(str(self.dataset.path))

    def run(self):  # pragma: no cover — intentional NIE
        raise NotImplementedError(
            "Engine.run() — full iterative loop — lands in Phase 2."
        )

    def recurse(self):  # pragma: no cover — intentional NIE
        raise NotImplementedError(
            "Engine.recurse() — the recursive auto-improve move — lands in Phase 3. "
            "Reads accumulated runs + meta_suggestions and mutates own prompt/policy."
        )
