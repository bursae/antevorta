from __future__ import annotations

import json

import geopandas as gpd

from antevorta.core.io import ensure_crs, read_geo_data, resolve_source
from antevorta.core.storage import ProjectPaths, ensure_project_dirs


def collect_aoi(cfg: dict) -> gpd.GeoDataFrame:
    paths = ProjectPaths(cfg["name"])
    ensure_project_dirs(paths)

    source = resolve_source(cfg["aoi"]["source"], cfg.get("_project_dir"))
    gdf = read_geo_data(source)
    gdf = ensure_crs(gdf, cfg["crs"])

    polygons = gdf[gdf.geometry.geom_type.isin(["Polygon", "MultiPolygon"])].copy()
    if polygons.empty:
        raise ValueError("AOI must contain Polygon or MultiPolygon geometry")

    union_geom = polygons.geometry.union_all()
    aoi = gpd.GeoDataFrame(
        {"aoi_id": [cfg["aoi"]["id"]], "geometry": [union_geom]},
        crs=cfg["crs"],
    )

    out = paths.processed / "aoi.parquet"
    aoi.to_parquet(out)

    meta = {
        "aoi_id": cfg["aoi"]["id"],
        "crs": cfg["crs"],
        "bounds": list(aoi.total_bounds),
        "area": float(aoi.geometry.area.iloc[0]),
        "output": str(out),
    }
    (paths.metadata / "aoi.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    return aoi
