from __future__ import annotations

from dataclasses import dataclass

import geopandas as gpd
import numpy as np
from shapely.geometry import Point, Polygon


@dataclass(frozen=True)
class SpatialBundle:
    gdf_wgs84: gpd.GeoDataFrame
    gdf_metric: gpd.GeoDataFrame


def require_wgs84(gdf: gpd.GeoDataFrame, name: str) -> gpd.GeoDataFrame:
    if gdf.crs is None:
        raise ValueError(f"{name} has no CRS; expected EPSG:4326 data")
    return gdf.to_crs(epsg=4326)


def as_metric(gdf_wgs84: gpd.GeoDataFrame) -> SpatialBundle:
    metric_crs = gdf_wgs84.estimate_utm_crs()
    if metric_crs is None:
        raise ValueError("Unable to estimate projected CRS for AOI")
    return SpatialBundle(gdf_wgs84=gdf_wgs84, gdf_metric=gdf_wgs84.to_crs(metric_crs))


def make_grid(aoi_metric: gpd.GeoDataFrame, resolution_m: float) -> gpd.GeoDataFrame:
    polygon = aoi_metric.geometry.iloc[0]
    if not isinstance(polygon, Polygon):
        raise ValueError("AOI must contain a polygon geometry")

    minx, miny, maxx, maxy = polygon.bounds
    xs = np.arange(minx, maxx, resolution_m)
    ys = np.arange(miny, maxy, resolution_m)
    cells: list[dict[str, object]] = []
    cell_id = 1

    for x in xs:
        for y in ys:
            center = Point(x + resolution_m / 2.0, y + resolution_m / 2.0)
            if polygon.contains(center):
                cells.append({"cell_id": cell_id, "geometry": center})
                cell_id += 1

    if not cells:
        raise ValueError("Grid generation produced no cells; adjust AOI or resolution")
    return gpd.GeoDataFrame(cells, geometry="geometry", crs=aoi_metric.crs)


def random_points_from_grid(
    grid_metric: gpd.GeoDataFrame,
    n_points: int,
    seed: int,
) -> gpd.GeoDataFrame:
    if n_points <= 0:
        raise ValueError("n_points must be > 0")
    if len(grid_metric) == 0:
        raise ValueError("Grid has no cells")

    sample_size = min(n_points, len(grid_metric))
    sampled = grid_metric.sample(n=sample_size, replace=False, random_state=seed)
    return sampled[["geometry"]].copy()
