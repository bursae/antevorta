from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


REQUIRED_ROOT_KEYS = {"name", "crs", "grid", "time", "aoi", "events"}


def load_project_config(project_yaml: str | Path) -> dict[str, Any]:
    path = Path(project_yaml)
    with path.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    missing = REQUIRED_ROOT_KEYS - set(cfg)
    if missing:
        raise ValueError(f"Missing required keys in {path}: {sorted(missing)}")

    if "cell_size_m" not in cfg["grid"]:
        raise ValueError("Missing required key: grid.cell_size_m")
    if "window_days" not in cfg["time"]:
        raise ValueError("Missing required key: time.window_days")

    cfg["_project_yaml"] = str(path)
    cfg["_project_dir"] = str(path.parent.resolve())
    return cfg
