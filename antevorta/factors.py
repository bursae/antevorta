from __future__ import annotations

from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np

from antevorta.project import ProjectState, load_manifest, save_manifest
from antevorta.io import copy_file, validate_factor_extension


def _factor_name(path: Path) -> str:
    return path.stem.replace(" ", "_").lower()


def _infer_factor_source(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".tif", ".tiff"}:
        return "raster"
    return "vector"


def _copy_factor_files(factor_path: Path, factors_dir: Path) -> Path:
    if factor_path.suffix.lower() == ".shp":
        stem = factor_path.stem
        for src in factor_path.parent.glob(f"{stem}.*"):
            copy_file(src, factors_dir / src.name)
        return factors_dir / factor_path.name
    return copy_file(factor_path, factors_dir / factor_path.name)


def add_factor(state: ProjectState, factor_path: Path, factor_type: str) -> dict[str, Any]:
    if factor_type != "distance":
        raise ValueError("Only factor type 'distance' is supported")

    validate_factor_extension(factor_path)
    manifest = load_manifest(state)
    stored = _copy_factor_files(factor_path, state.factors_dir)
    source = _infer_factor_source(stored)

    factor = {
        "name": _factor_name(stored),
        "path": str(stored.resolve()),
        "source": source,
        "metric": "distance" if source == "vector" else "raster_value",
    }

    existing = manifest.get("factors", [])
    if not isinstance(existing, list):
        raise ValueError("Invalid project manifest: factors must be a list")
    existing = [x for x in existing if x.get("name") != factor["name"]]
    existing.append(factor)
    manifest["factors"] = existing
    save_manifest(state, manifest)
    return factor


def load_factors(state: ProjectState) -> list[dict[str, Any]]:
    manifest = load_manifest(state)
    factors = manifest.get("factors", [])
    if not isinstance(factors, list):
        raise ValueError("Invalid project manifest: factors must be a list")
    if len(factors) == 0:
        raise ValueError("No factors registered. Run: antevorta add-factor <file> --type distance")
    return factors


def _score_vector_distance(points_metric: gpd.GeoDataFrame, factor_path: Path) -> np.ndarray:
    factor = gpd.read_file(factor_path)
    if factor.empty:
        raise ValueError(f"Factor has no features: {factor_path}")
    if factor.crs is None:
        raise ValueError(f"Vector factor missing CRS: {factor_path}")
    geom = factor.to_crs(points_metric.crs).geometry.unary_union
    distances = points_metric.geometry.distance(geom).to_numpy(dtype=float)
    return distances


def _score_raster_value(points_wgs84: gpd.GeoDataFrame, factor_path: Path) -> np.ndarray:
    try:
        import rasterio
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "rasterio is required for raster factors (.tif/.tiff). Install rasterio to use this factor type."
        ) from exc

    with rasterio.open(factor_path) as src:
        points = points_wgs84.to_crs(src.crs)
        coords = [(geom.x, geom.y) for geom in points.geometry]
        values = [v[0] for v in src.sample(coords)]
        arr = np.array(values, dtype=float)

        nodata = src.nodata
        if nodata is not None:
            arr = np.where(arr == nodata, np.nan, arr)

    if np.isnan(arr).any():
        # Keep deterministic behavior while handling sparse nodata samples.
        fill_value = float(np.nanmean(arr)) if not np.isnan(np.nanmean(arr)) else 0.0
        arr = np.nan_to_num(arr, nan=fill_value)
    return arr


def score_points_for_factor(
    points_wgs84: gpd.GeoDataFrame,
    points_metric: gpd.GeoDataFrame,
    factor: dict[str, Any],
) -> np.ndarray:
    factor_path = Path(str(factor["path"]))
    source = str(factor["source"])
    if source == "vector":
        return _score_vector_distance(points_metric, factor_path)
    if source == "raster":
        return _score_raster_value(points_wgs84, factor_path)
    raise ValueError(f"Unknown factor source: {source}")
