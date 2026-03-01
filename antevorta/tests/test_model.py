from __future__ import annotations

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point, Polygon

from antevorta.events import add_events, load_events_geodataframe
from antevorta.factors import add_factor, load_factors
from antevorta.grid import build_grid, load_grid
from antevorta.model import build_feature_matrix, build_training_data, predict_likelihood, train_logistic_regression
from antevorta.project import ProjectState, initialize_project


def test_factor_scoring_and_model_training(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    aoi = gpd.GeoDataFrame(
        [{"geometry": Polygon([(-0.03, -0.03), (-0.03, 0.03), (0.03, 0.03), (0.03, -0.03)])}],
        crs="EPSG:4326",
    )
    aoi_path = tmp_path / "aoi.geojson"
    aoi.to_file(aoi_path, driver="GeoJSON")

    events_df = pd.DataFrame(
        {
            "id": ["e1", "e2", "e3", "e4"],
            "latitude": [0.001, 0.002, -0.001, -0.002],
            "longitude": [0.001, -0.001, 0.002, -0.002],
            "timestamp": [
                "2024-01-01T00:00:00Z",
                "2024-01-02T00:00:00Z",
                "2024-01-03T00:00:00Z",
                "2024-01-04T00:00:00Z",
            ],
        }
    )
    events_path = tmp_path / "events.csv"
    events_df.to_csv(events_path, index=False)

    factor = gpd.GeoDataFrame([{"geometry": Point(0.0, 0.0)}], crs="EPSG:4326")
    factor_path = tmp_path / "factor.geojson"
    factor.to_file(factor_path, driver="GeoJSON")

    initialize_project(aoi_path)
    state = ProjectState.from_cwd()
    add_events(state, events_path)
    add_factor(state, factor_path, "distance")
    build_grid(state, resolution_m=500)

    events = load_events_geodataframe(state.data_dir / "events.csv")
    grid = load_grid(state)
    factors = load_factors(state)

    event_features = build_feature_matrix(events, factors)
    grid_features = build_feature_matrix(grid, factors)
    assert event_features.columns.tolist() == ["factor"]
    assert float(event_features["factor"].mean()) < float(grid_features["factor"].mean())

    training = build_training_data(events, grid, factors)
    fitted = train_logistic_regression(training)
    ranked = predict_likelihood(fitted, grid, factors)

    assert fitted.estimator.coef_.shape == (1, 1)
    assert ranked["likelihood"].between(0.0, 1.0).all()
