from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pandas as pd


ALLOWED_FACTOR_EXTENSIONS = {".geojson", ".shp", ".tif", ".tiff"}


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Expected object JSON in {path}")
    return data


def write_json(path: Path, payload: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def copy_file(src: Path, dst: Path) -> Path:
    ensure_dir(dst.parent)
    shutil.copy2(src, dst)
    return dst


def read_events_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def write_dataframe_csv(df: pd.DataFrame, path: Path) -> None:
    ensure_dir(path.parent)
    df.to_csv(path, index=False)


def validate_factor_extension(path: Path) -> None:
    if path.suffix.lower() not in ALLOWED_FACTOR_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_FACTOR_EXTENSIONS))
        raise ValueError(f"Unsupported factor file extension {path.suffix}. Allowed: {allowed}")
