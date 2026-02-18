from __future__ import annotations

import json

import geopandas as gpd

from antevorta.core.io import ensure_crs, read_geo_data, resolve_source
from antevorta.core.storage import ProjectPaths, ensure_project_dirs


def collect_factors(cfg: dict) -> list[dict]:
    paths = ProjectPaths(cfg["name"])
    ensure_project_dirs(paths)

    aoi = gpd.read_parquet(paths.processed / "aoi.parquet")
    layers = []

    for factor in cfg.get("factors", []):
        gdf = read_geo_data(
            source=resolve_source(factor["source"], cfg.get("_project_dir")),
            source_format=factor.get("format"),
            lat_field=factor.get("geometry", {}).get("lat_field"),
            lon_field=factor.get("geometry", {}).get("lon_field"),
        )
        gdf = ensure_crs(gdf, cfg["crs"])
        gdf = gpd.clip(gdf, aoi)

        out = paths.factors_dir / f"{factor['name']}.parquet"
        gdf.to_parquet(out)

        layers.append(
            {
                "name": factor["name"],
                "agg": factor.get("agg"),
                "geometry_type": factor.get("geometry_type"),
                "fields": factor.get("fields", []),
                "weight_field": factor.get("weight_field"),
                "path": str(out),
            }
        )

    (paths.metadata / "factors.json").write_text(json.dumps(layers, indent=2), encoding="utf-8")
    return layers
