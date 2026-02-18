from __future__ import annotations

import geopandas as gpd
import pandas as pd

from antevorta.core.io import ensure_crs, read_geo_data, resolve_source
from antevorta.core.storage import ProjectPaths, ensure_project_dirs


def collect_events(cfg: dict) -> gpd.GeoDataFrame:
    paths = ProjectPaths(cfg["name"])
    ensure_project_dirs(paths)

    event_cfg = cfg["events"]
    geom_cfg = event_cfg.get("geometry", {})

    events = read_geo_data(
        source=resolve_source(event_cfg["source"], cfg.get("_project_dir")),
        source_format=event_cfg.get("format"),
        lat_field=geom_cfg.get("lat_field"),
        lon_field=geom_cfg.get("lon_field"),
    )
    events = ensure_crs(events, cfg["crs"])

    time_field = event_cfg["time_field"]
    if time_field not in events.columns:
        raise ValueError(f"Missing configured events.time_field: {time_field}")

    events["event_time"] = pd.to_datetime(events[time_field], errors="coerce", utc=True)
    events = events.dropna(subset=["event_time", "geometry"]).copy()

    if "event_type" not in events.columns:
        events["event_type"] = None

    aoi = gpd.read_parquet(paths.processed / "aoi.parquet")
    events = gpd.clip(events, aoi)

    window_days = int(cfg["time"]["window_days"])
    max_t = events["event_time"].max()
    min_t = max_t - pd.Timedelta(days=window_days - 1)
    events = events[events["event_time"] >= min_t].copy()

    events = events[["event_time", "event_type", "geometry"]]
    out = paths.processed / "events.parquet"
    events.to_parquet(out)
    return events
