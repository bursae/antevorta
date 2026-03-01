from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd

from antevorta.io import write_dataframe_csv


def export_assessment(
    grid_wgs84: gpd.GeoDataFrame,
    ranked_grid: pd.DataFrame,
    weights: pd.DataFrame,
    output_dir: Path,
) -> dict[str, Path]:
    lookup = ranked_grid.set_index("cell_id")
    geo = grid_wgs84[["cell_id", "geometry"]].copy()
    geo["probability"] = geo["cell_id"].map(lookup["probability"])
    geo["likelihood"] = geo["cell_id"].map(lookup["likelihood"])

    likelihood_path = output_dir / "likelihood_grid.geojson"
    ranked_path = output_dir / "ranked_grid.csv"
    weights_path = output_dir / "factor_weights.csv"

    geo.to_file(likelihood_path, driver="GeoJSON")
    write_dataframe_csv(ranked_grid, ranked_path)
    write_dataframe_csv(weights, weights_path)

    return {
        "likelihood_grid": likelihood_path,
        "ranked_grid": ranked_path,
        "factor_weights": weights_path,
    }
