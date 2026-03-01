from __future__ import annotations

import geopandas as gpd
from shapely.geometry import Polygon

from antevorta.grid import build_grid
from antevorta.project import ProjectState, initialize_project


def test_build_grid_generates_cells(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    aoi = gpd.GeoDataFrame(
        [{"geometry": Polygon([(-0.02, -0.02), (-0.02, 0.02), (0.02, 0.02), (0.02, -0.02)])}],
        crs="EPSG:4326",
    )
    aoi_path = tmp_path / "aoi.geojson"
    aoi.to_file(aoi_path, driver="GeoJSON")

    initialize_project(aoi_path)
    state = ProjectState.from_cwd()
    grid_path = build_grid(state, resolution_m=500)

    grid = gpd.read_file(grid_path)
    assert len(grid) > 0
    assert {"cell_id", "latitude", "longitude", "geometry"}.issubset(grid.columns)
