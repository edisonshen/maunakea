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
