from __future__ import annotations

import geopandas as gpd
import pandas as pd



def build_events_grid_daily(grid: gpd.GeoDataFrame, events: gpd.GeoDataFrame, window_days: int) -> pd.DataFrame:
    events = events.copy()
    events["date"] = pd.to_datetime(events["event_time"]).dt.floor("D").dt.tz_localize(None)

    joined = gpd.sjoin(
        events[["date", "geometry"]],
        grid[["grid_id", "geometry"]],
        how="inner",
        predicate="within",
    )

    daily = (
        joined.groupby(["grid_id", "date"], as_index=False)
        .size()
        .rename(columns={"size": "event_count"})
    )

    if daily.empty:
        last_date = pd.Timestamp.today().floor("D")
    else:
        last_date = daily["date"].max()

    dates = pd.date_range(end=last_date, periods=window_days, freq="D")
    panel = pd.MultiIndex.from_product(
        [grid["grid_id"].values, dates], names=["grid_id", "date"]
    ).to_frame(index=False)

    out = panel.merge(daily, on=["grid_id", "date"], how="left")
    out["event_count"] = out["event_count"].fillna(0).astype(int)
    out = out.sort_values(["grid_id", "date"]).reset_index(drop=True)
    out["roll_7d_event_count"] = (
        out.groupby("grid_id")["event_count"]
        .rolling(window=7, min_periods=1)
        .sum()
        .reset_index(level=0, drop=True)
    )
    return out
