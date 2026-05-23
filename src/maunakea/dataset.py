"""Generic dataset adapter. Parquet-only in MVP.

A `Dataset` points at either:
  - a directory of `*.parquet` files (each becomes a named "table"), or
  - a single `*.parquet` file (treated as a one-table dataset).
"""

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
