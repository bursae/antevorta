from __future__ import annotations

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point


URL_PREFIXES = ("http://", "https://", "s3://")


def resolve_source(source: str, project_dir: str | None = None) -> str:
    if source.startswith(URL_PREFIXES):
        return source
    path = Path(source)
    if path.is_absolute() or path.exists() or not project_dir:
        return str(path)
    return str((Path(project_dir) / path).resolve())


def infer_format(source: str) -> str:
    src = source.lower()
    if src.endswith(".parquet"):
        return "parquet"
    if src.endswith(".csv"):
        return "csv"
    if src.endswith(".geojson") or src.endswith(".json"):
        return "geojson"
    if src.endswith(".shp"):
        return "shp"
    raise ValueError(f"Could not infer format from source: {source}")


def read_geo_data(
    source: str,
    source_format: str | None = None,
    lat_field: str | None = None,
    lon_field: str | None = None,
) -> gpd.GeoDataFrame:
    fmt = (source_format or infer_format(source)).lower()

    if fmt == "csv":
        if not lat_field or not lon_field:
            raise ValueError("CSV sources require geometry.lat_field and geometry.lon_field")
        df = pd.read_csv(source)
        geometry = gpd.GeoSeries(
            [Point(xy) for xy in zip(df[lon_field], df[lat_field])], crs="EPSG:4326"
        )
        return gpd.GeoDataFrame(df, geometry=geometry)

    if fmt == "parquet":
        return gpd.read_parquet(source)

    if fmt in {"geojson", "shp"}:
        return gpd.read_file(source)

    raise ValueError(f"Unsupported source format: {fmt}")


def ensure_crs(gdf: gpd.GeoDataFrame, target_crs: str) -> gpd.GeoDataFrame:
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326")
    return gdf.to_crs(target_crs)
