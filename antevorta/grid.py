from __future__ import annotations

from pathlib import Path

import geopandas as gpd

from antevorta.project import ProjectState, load_manifest, save_manifest
from antevorta.spatial import as_metric, make_grid, require_wgs84


def load_aoi(aoi_path: Path) -> gpd.GeoDataFrame:
    aoi = gpd.read_file(aoi_path)
    if aoi.empty:
        raise ValueError("AOI file is empty")
    aoi = require_wgs84(aoi, "AOI")
    aoi = aoi.explode(index_parts=False, ignore_index=True)
    if len(aoi) != 1:
        raise ValueError("AOI must contain exactly one polygon feature")
    if aoi.geometry.iloc[0].geom_type not in {"Polygon", "MultiPolygon"}:
        raise ValueError("AOI must be a polygon geometry")
    aoi = aoi[["geometry"]].copy()
    return aoi


def build_grid(state: ProjectState, resolution_m: float) -> Path:
    if resolution_m <= 0:
        raise ValueError("Resolution must be > 0 meters")

    manifest = load_manifest(state)
    aoi_path = manifest.get("aoi_path")
    if not isinstance(aoi_path, str):
        raise ValueError("Project is missing AOI path")

    aoi = load_aoi(Path(aoi_path))
    bundle = as_metric(aoi)
    grid_metric = make_grid(bundle.gdf_metric, resolution_m)
    grid_wgs84 = grid_metric.to_crs(epsg=4326)
    grid_wgs84["latitude"] = grid_wgs84.geometry.y
    grid_wgs84["longitude"] = grid_wgs84.geometry.x

    grid_path = state.data_dir / "grid.geojson"
    grid_wgs84.to_file(grid_path, driver="GeoJSON")
    manifest["grid_path"] = str(grid_path.resolve())
    save_manifest(state, manifest)
    return grid_path


def load_grid(state: ProjectState) -> gpd.GeoDataFrame:
    manifest = load_manifest(state)
    grid_path = manifest.get("grid_path")
    if not isinstance(grid_path, str):
        raise ValueError("Grid not found. Run: antevorta build-grid --resolution <meters>")
    grid = gpd.read_file(grid_path)
    if grid.empty:
        raise ValueError("Grid is empty")
    return require_wgs84(grid, "Grid")
