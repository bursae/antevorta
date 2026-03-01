from __future__ import annotations

from dataclasses import dataclass

import geopandas as gpd
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from antevorta.config import CONFIG
from antevorta.factors import score_points_for_factor
from antevorta.spatial import as_metric, random_points_from_grid


@dataclass
class TrainingData:
    x: pd.DataFrame
    y: pd.Series


@dataclass
class FittedModel:
    estimator: LogisticRegression
    feature_names: list[str]


def build_feature_matrix(
    points_wgs84: gpd.GeoDataFrame,
    factors: list[dict[str, object]],
) -> pd.DataFrame:
    metric_points = as_metric(points_wgs84).gdf_metric
    data: dict[str, np.ndarray] = {}
    for factor in factors:
        name = str(factor["name"])
        data[name] = score_points_for_factor(points_wgs84, metric_points, factor)
    return pd.DataFrame(data)


def build_training_data(
    events_wgs84: gpd.GeoDataFrame,
    grid_wgs84: gpd.GeoDataFrame,
    factors: list[dict[str, object]],
    seed: int = CONFIG.seed,
    background_multiplier: int = CONFIG.background_multiplier,
) -> TrainingData:
    if len(events_wgs84) == 0:
        raise ValueError("No events found")
    if len(grid_wgs84) == 0:
        raise ValueError("No grid cells found")

    event_x = build_feature_matrix(events_wgs84, factors)
    n_background = max(1, len(events_wgs84) * background_multiplier)
    grid_metric = as_metric(grid_wgs84).gdf_metric
    background_metric = random_points_from_grid(grid_metric, n_background, seed)
    background_wgs84 = background_metric.to_crs(epsg=4326)
    background_x = build_feature_matrix(background_wgs84, factors)

    x = pd.concat([event_x, background_x], axis=0, ignore_index=True)
    y = pd.Series(
        np.concatenate(
            [np.ones(len(event_x), dtype=int), np.zeros(len(background_x), dtype=int)]
        ),
        name="label",
    )
    return TrainingData(x=x, y=y)


def train_logistic_regression(data: TrainingData, seed: int = CONFIG.seed) -> FittedModel:
    if data.y.nunique() < 2:
        raise ValueError("Training labels must include both event and background classes")

    estimator = LogisticRegression(
        solver="lbfgs",
        random_state=seed,
        max_iter=1000,
    )
    estimator.fit(data.x, data.y)
    return FittedModel(estimator=estimator, feature_names=list(data.x.columns))


def predict_likelihood(
    model: FittedModel,
    grid_wgs84: gpd.GeoDataFrame,
    factors: list[dict[str, object]],
) -> pd.DataFrame:
    features = build_feature_matrix(grid_wgs84, factors)
    proba = model.estimator.predict_proba(features)[:, 1]

    p_min = float(np.min(proba))
    p_max = float(np.max(proba))
    if p_max > p_min:
        normalized = (proba - p_min) / (p_max - p_min)
    else:
        normalized = np.zeros_like(proba)

    out = pd.DataFrame(
        {
            "cell_id": grid_wgs84["cell_id"].astype(int).to_numpy(),
            "latitude": grid_wgs84.geometry.y.to_numpy(),
            "longitude": grid_wgs84.geometry.x.to_numpy(),
            "probability": proba,
            "likelihood": normalized,
        }
    )
    return out.sort_values("likelihood", ascending=False).reset_index(drop=True)


def factor_weights(model: FittedModel) -> pd.DataFrame:
    weights = model.estimator.coef_[0]
    return pd.DataFrame({"factor": model.feature_names, "weight": weights}).sort_values(
        "weight", ascending=False
    )
