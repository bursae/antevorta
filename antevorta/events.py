from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd

from antevorta.project import ProjectState, load_manifest, save_manifest
from antevorta.io import read_events_csv


REQUIRED_EVENT_COLUMNS = {"id", "latitude", "longitude", "timestamp"}


def validate_events(events: pd.DataFrame) -> pd.DataFrame:
    missing = REQUIRED_EVENT_COLUMNS - set(events.columns)
    if missing:
        missing_str = ", ".join(sorted(missing))
        raise ValueError(f"Events CSV is missing required columns: {missing_str}")

    typed = events.copy()
    typed["latitude"] = pd.to_numeric(typed["latitude"], errors="raise")
    typed["longitude"] = pd.to_numeric(typed["longitude"], errors="raise")
    typed["timestamp"] = pd.to_datetime(typed["timestamp"], errors="raise", utc=True)

    if typed["latitude"].isna().any() or typed["longitude"].isna().any():
        raise ValueError("Events CSV has null coordinates")

    if not typed["latitude"].between(-90, 90).all():
        raise ValueError("Latitude must be between -90 and 90")
    if not typed["longitude"].between(-180, 180).all():
        raise ValueError("Longitude must be between -180 and 180")

    if typed["id"].duplicated().any():
        raise ValueError("Event id values must be unique")

    return typed


def _events_from_csv(events_path: Path, time_field: str) -> pd.DataFrame:
    events = read_events_csv(events_path)
    if time_field != "timestamp":
        if time_field not in events.columns:
            raise ValueError(f"Events CSV is missing required time field: {time_field}")
        if "timestamp" in events.columns and time_field != "timestamp":
            events = events.drop(columns=["timestamp"])
        events = events.rename(columns={time_field: "timestamp"})
    return events


def _events_from_geojson(events_path: Path, time_field: str) -> pd.DataFrame:
    gdf = gpd.read_file(events_path)
    if gdf.empty:
        raise ValueError("Events GeoJSON has no features")
    if gdf.geometry.is_empty.any():
        raise ValueError("Events GeoJSON contains empty geometry")
    if not gdf.geometry.geom_type.eq("Point").all():
        raise ValueError("Events GeoJSON must contain Point geometries only")
    if time_field not in gdf.columns:
        raise ValueError(f"Events GeoJSON is missing required time field: {time_field}")

    if gdf.crs is None:
        gdf = gdf.set_crs(epsg=4326)
    points = gdf.to_crs(epsg=4326)
    events = pd.DataFrame(
        {
            "id": [f"event_{i + 1}" for i in range(len(points))],
            "latitude": points.geometry.y.to_numpy(),
            "longitude": points.geometry.x.to_numpy(),
            "timestamp": points[time_field].to_numpy(),
        }
    )
    return events


def _load_events(events_path: Path, time_field: str) -> pd.DataFrame:
    suffix = events_path.suffix.lower()
    if suffix == ".csv":
        return _events_from_csv(events_path, time_field=time_field)
    if suffix == ".geojson":
        return _events_from_geojson(events_path, time_field=time_field)
    raise ValueError("Events must be .csv or .geojson")


def add_events(state: ProjectState, events_path: Path, time_field: str = "timestamp") -> Path:
    manifest = load_manifest(state)
    events = validate_events(_load_events(events_path, time_field=time_field))
    stored_path = state.data_dir / "events.csv"
    events.to_csv(stored_path, index=False)
    manifest["events_path"] = str(stored_path.resolve())
    save_manifest(state, manifest)
    return stored_path


def load_events_geodataframe(events_csv: Path) -> gpd.GeoDataFrame:
    events = validate_events(_load_events(events_csv, time_field="timestamp"))
    gdf = gpd.GeoDataFrame(
        events,
        geometry=gpd.points_from_xy(events["longitude"], events["latitude"]),
        crs="EPSG:4326",
    )
    return gdf
