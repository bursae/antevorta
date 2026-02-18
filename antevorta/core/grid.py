from __future__ import annotations

import numpy as np
import geopandas as gpd
from shapely.geometry import box


def build_grid(aoi: gpd.GeoDataFrame, cell_size_m: float, project_name: str) -> gpd.GeoDataFrame:
    geom = aoi.geometry.union_all()
    minx, miny, maxx, maxy = geom.bounds

    xs = np.arange(minx, maxx + cell_size_m, cell_size_m)
    ys = np.arange(miny, maxy + cell_size_m, cell_size_m)

    cells = [box(x, y, x + cell_size_m, y + cell_size_m) for x in xs[:-1] for y in ys[:-1]]
    grid = gpd.GeoDataFrame({"geometry": cells}, crs=aoi.crs)
    grid = gpd.clip(grid, aoi)
    grid = grid[~grid.geometry.is_empty].copy()
    grid = grid.reset_index(drop=True)
    grid["grid_id"] = [f"{project_name}_{i:07d}" for i in range(len(grid))]
    return grid[["grid_id", "geometry"]]
