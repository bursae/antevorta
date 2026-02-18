from __future__ import annotations

import geopandas as gpd
import pandas as pd

from antevorta.core.storage import ProjectPaths
from antevorta.features.events import build_events_grid_daily
from antevorta.features.factors import build_factors_grid


def build_dataset(cfg: dict) -> pd.DataFrame:
    paths = ProjectPaths(cfg["name"])

    grid = gpd.read_parquet(paths.processed / "grid.parquet")
    events = gpd.read_parquet(paths.processed / "events.parquet")

    events_grid_daily = build_events_grid_daily(
        grid=grid,
        events=events,
        window_days=int(cfg["time"]["window_days"]),
    )

    factors_grid = build_factors_grid(
        grid=grid,
        cfg=cfg,
        factors_dir=str(paths.factors_dir),
    )

    table = events_grid_daily.merge(factors_grid, on="grid_id", how="left")

    table = table.sort_values(["grid_id", "date"]).reset_index(drop=True)
    table["target_next_day"] = (
        table.groupby("grid_id")["event_count"].shift(-1).fillna(0) > 0
    ).astype(int)

    factor_cols = [c for c in table.columns if c.startswith("factor_")]
    if factor_cols:
        table[factor_cols] = table[factor_cols].fillna(0.0)

    out = paths.processed / "model_table.parquet"
    table.to_parquet(out, index=False)
    return table
