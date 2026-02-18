from __future__ import annotations

import geopandas as gpd
import pandas as pd



def _grid_base(grid: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    base = grid[["grid_id", "geometry"]].copy()
    base["cell_area"] = base.geometry.area
    return base


def aggregate_coverage_pct(grid: gpd.GeoDataFrame, factor_gdf: gpd.GeoDataFrame, name: str) -> pd.DataFrame:
    base = _grid_base(grid)
    inter = gpd.overlay(base, factor_gdf[["geometry"]], how="intersection")
    if inter.empty:
        return pd.DataFrame({"grid_id": grid["grid_id"], f"factor_{name}": 0.0})

    inter["coverage"] = inter.geometry.area / inter["cell_area"]
    agg = inter.groupby("grid_id", as_index=False)["coverage"].sum()
    agg = agg.rename(columns={"coverage": f"factor_{name}"})
    return pd.DataFrame({"grid_id": grid["grid_id"]}).merge(agg, on="grid_id", how="left").fillna(0.0)


def aggregate_length_weighted(
    grid: gpd.GeoDataFrame,
    factor_gdf: gpd.GeoDataFrame,
    name: str,
    weight_field: str | None = None,
) -> pd.DataFrame:
    base = _grid_base(grid)

    cols = ["geometry"]
    if weight_field and weight_field in factor_gdf.columns:
        cols.append(weight_field)

    inter = gpd.overlay(base, factor_gdf[cols], how="intersection")
    if inter.empty:
        return pd.DataFrame({"grid_id": grid["grid_id"], f"factor_{name}": 0.0})

    inter["weight"] = inter[weight_field] if weight_field and weight_field in inter.columns else 1.0
    inter["value"] = (inter.geometry.length * inter["weight"]) / inter["cell_area"]
    agg = inter.groupby("grid_id", as_index=False)["value"].sum().rename(columns={"value": f"factor_{name}"})
    return pd.DataFrame({"grid_id": grid["grid_id"]}).merge(agg, on="grid_id", how="left").fillna(0.0)


def aggregate_area_weighted(
    grid: gpd.GeoDataFrame,
    factor_gdf: gpd.GeoDataFrame,
    name: str,
    fields: list[str],
) -> pd.DataFrame:
    base = _grid_base(grid)
    available_fields = [f for f in fields if f in factor_gdf.columns]
    if not available_fields:
        raise ValueError(f"No configured fields found for factor '{name}'. fields={fields}")

    inter = gpd.overlay(base, factor_gdf[["geometry", *available_fields]], how="intersection")
    if inter.empty:
        out = pd.DataFrame({"grid_id": grid["grid_id"]})
        for field in available_fields:
            out[f"factor_{name}_{field}"] = 0.0
        return out

    overlap_ratio = inter.geometry.area / inter["cell_area"]
    out = pd.DataFrame({"grid_id": grid["grid_id"]})

    for field in available_fields:
        inter[f"weighted_{field}"] = inter[field].fillna(0) * overlap_ratio
        agg = (
            inter.groupby("grid_id", as_index=False)[f"weighted_{field}"]
            .sum()
            .rename(columns={f"weighted_{field}": f"factor_{name}_{field}"})
        )
        out = out.merge(agg, on="grid_id", how="left")

    fill_cols = [c for c in out.columns if c != "grid_id"]
    out[fill_cols] = out[fill_cols].fillna(0.0)
    return out


def build_factors_grid(grid: gpd.GeoDataFrame, cfg: dict, factors_dir: str) -> pd.DataFrame:
    out = pd.DataFrame({"grid_id": grid["grid_id"]})

    for factor in cfg.get("factors", []):
        name = factor["name"]
        gdf = gpd.read_parquet(f"{factors_dir}/{name}.parquet")
        agg = factor["agg"]

        if agg == "coverage_pct":
            factor_df = aggregate_coverage_pct(grid, gdf, name)
        elif agg == "length_weighted":
            factor_df = aggregate_length_weighted(grid, gdf, name, factor.get("weight_field"))
        elif agg == "area_weighted":
            factor_df = aggregate_area_weighted(grid, gdf, name, factor.get("fields", []))
        else:
            raise ValueError(f"Unsupported factor aggregation: {agg}")

        out = out.merge(factor_df, on="grid_id", how="left")

    fill_cols = [c for c in out.columns if c != "grid_id"]
    if fill_cols:
        out[fill_cols] = out[fill_cols].fillna(0.0)
    return out
