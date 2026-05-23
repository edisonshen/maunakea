"""End-to-end smoke tests.

`test_cli_version` is the A3 anchor. `test_no_rainier_import_in_src` is the A4
decoupling invariant — CI also runs `rg` directly as a job-level gate.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def test_cli_version():
    out = subprocess.check_output(
        [sys.executable, "-m", "maunakea.cli", "--version"], text=True
    )
    assert "0.0.1" in out


def test_no_rainier_import_in_src():
    """A4 decoupling invariant: zero references to 'rainier' in src/maunakea/."""
    src_dir = Path(__file__).resolve().parent.parent / "src" / "maunakea"
    assert src_dir.exists()

    if shutil.which("rg") is not None:
        # ripgrep present (operator's box) — exit code 1 means "no matches".
        result = subprocess.run(
            ["rg", "-l", "rainier", str(src_dir)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1, (
            f"unexpected rainier refs: {result.stdout}"
        )
    else:
        # CI fallback — plain-Python grep across .py files.
        matches: list[str] = []
        for p in src_dir.rglob("*.py"):
            if "rainier" in p.read_text():
                matches.append(str(p))
        assert not matches, f"unexpected rainier refs: {matches}"


def test_cli_suggest_invokes_engine(synthetic_cache, mock_litellm, tmp_data_dir):
    """CLI `suggest` exits 0 and prints both sections (A7)."""
    from click.testing import CliRunner

    from maunakea.cli import main

    runner = CliRunner()
    result = runner.invoke(
        main,
        ["suggest", "--dataset", str(synthetic_cache), "--goal", "predict 30d returns"],
    )
    assert result.exit_code == 0, result.output
    assert "Research suggestion:" in result.output
    assert "Meta-suggestion" in result.output


def test_cli_suggest_with_critique(synthetic_cache, mock_litellm, tmp_data_dir):
    from click.testing import CliRunner

    from maunakea.cli import main

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "suggest",
            "--dataset",
            str(synthetic_cache),
            "--goal",
            "x",
            "--critique",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "Critique:" in result.output


def test_cli_history_round_trip(synthetic_cache, mock_litellm, tmp_data_dir):
    """A8: `maunakea history` reads back what `suggest` just wrote."""
    from click.testing import CliRunner

    from maunakea.cli import main

    runner = CliRunner()
    r1 = runner.invoke(
        main,
        ["suggest", "--dataset", str(synthetic_cache), "--goal", "x"],
    )
    assert r1.exit_code == 0, r1.output
    r2 = runner.invoke(main, ["history", "--dataset", str(synthetic_cache)])
    assert r2.exit_code == 0, r2.output
    assert "run(s) found" in r2.output


def test_cli_history_empty(synthetic_cache, tmp_data_dir):
    from click.testing import CliRunner

    from maunakea.cli import main

    runner = CliRunner()
    r = runner.invoke(main, ["history", "--dataset", str(synthetic_cache)])
    assert r.exit_code == 0
    assert "no prior runs" in r.output
