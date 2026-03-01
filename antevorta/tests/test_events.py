from __future__ import annotations

import geopandas as gpd
from shapely.geometry import Point, Polygon

from antevorta.events import add_events, load_events_geodataframe
from antevorta.project import ProjectState, initialize_project


def test_add_events_accepts_geojson(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    aoi = gpd.GeoDataFrame(
        [{"geometry": Polygon([(-0.03, -0.03), (-0.03, 0.03), (0.03, 0.03), (0.03, -0.03)])}],
        crs="EPSG:4326",
    )
    aoi_path = tmp_path / "aoi.geojson"
    aoi.to_file(aoi_path, driver="GeoJSON")

    events = gpd.GeoDataFrame(
        [{"event_time": "2024-01-01T00:00:00Z"}, {"event_time": "2024-01-02T00:00:00Z"}],
        geometry=[Point(0.001, 0.001), Point(-0.001, -0.001)],
        crs="EPSG:4326",
    )
    events_path = tmp_path / "events.geojson"
    events.to_file(events_path, driver="GeoJSON")

    initialize_project(aoi_path)
    state = ProjectState.from_cwd()
    stored = add_events(state, events_path, time_field="event_time")
    loaded = load_events_geodataframe(stored)

    assert stored.name == "events.csv"
    assert len(loaded) == 2
    assert set(loaded.columns) >= {"id", "latitude", "longitude", "timestamp", "geometry"}
