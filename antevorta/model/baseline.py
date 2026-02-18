from __future__ import annotations

import json
from dataclasses import dataclass

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import precision_score, recall_score, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from antevorta.core.storage import ProjectPaths


@dataclass
class TrainResult:
    metrics: dict
    model_path: str


def _feature_columns(table: pd.DataFrame) -> list[str]:
    drop_cols = {"grid_id", "date", "target_next_day"}
    return [c for c in table.columns if c not in drop_cols]


def train_baseline(cfg: dict, test_days: int = 30) -> TrainResult:
    paths = ProjectPaths(cfg["name"])
    table = pd.read_parquet(paths.processed / "model_table.parquet")
    table["date"] = pd.to_datetime(table["date"])

    last_date = table["date"].max()
    split_date = last_date - pd.Timedelta(days=test_days)

    feature_cols = _feature_columns(table)

    train_df = table[table["date"] <= split_date]
    test_df = table[table["date"] > split_date]

    if train_df.empty or test_df.empty:
        raise ValueError("Not enough data for time split. Increase window_days or reduce test_days.")

    X_train = train_df[feature_cols].fillna(0)
    y_train = train_df["target_next_day"].astype(int)
    X_test = test_df[feature_cols].fillna(0)
    y_test = test_df["target_next_day"].astype(int)

    model = Pipeline(
        steps=[
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(max_iter=1000, class_weight="balanced")),
        ]
    )
    model.fit(X_train, y_train)

    proba = model.predict_proba(X_test)[:, 1]
    pred = (proba >= 0.5).astype(int)

    metrics = {
        "project": cfg["name"],
        "model": "logistic_regression",
        "train_rows": int(len(train_df)),
        "test_rows": int(len(test_df)),
        "test_period_start": str(test_df["date"].min().date()),
        "test_period_end": str(test_df["date"].max().date()),
        "auc": float(roc_auc_score(y_test, proba)) if y_test.nunique() > 1 else None,
        "precision": float(precision_score(y_test, pred, zero_division=0)),
        "recall": float(recall_score(y_test, pred, zero_division=0)),
        "calibration_mean_pred": float(np.mean(proba)),
        "calibration_event_rate": float(np.mean(y_test)),
    }

    artifact = {
        "model": model,
        "feature_cols": feature_cols,
    }

    model_path = paths.models / "model.pkl"
    joblib.dump(artifact, model_path)

    (paths.reports / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return TrainResult(metrics=metrics, model_path=str(model_path))


def predict_risk(cfg: dict, as_of_date: str | None = None) -> pd.DataFrame:
    paths = ProjectPaths(cfg["name"])
    table = pd.read_parquet(paths.processed / "model_table.parquet")
    table["date"] = pd.to_datetime(table["date"]) 

    artifact = joblib.load(paths.models / "model.pkl")
    model = artifact["model"]
    feature_cols = artifact["feature_cols"]

    if as_of_date:
        as_of = pd.Timestamp(as_of_date)
    else:
        as_of = table["date"].max()

    latest = table[table["date"] == as_of].copy()
    if latest.empty:
        raise ValueError(f"No rows found for prediction date: {as_of.date()}")

    latest["risk_score"] = model.predict_proba(latest[feature_cols].fillna(0))[:, 1]
    latest = latest.sort_values("risk_score", ascending=False).reset_index(drop=True)
    latest["risk_rank"] = np.arange(1, len(latest) + 1)

    n = len(latest)
    latest["risk_band"] = "low"
    latest.loc[latest["risk_rank"] <= max(1, int(n * 0.20)), "risk_band"] = "top_20pct"
    latest.loc[latest["risk_rank"] <= max(1, int(n * 0.05)), "risk_band"] = "top_5pct"
    latest.loc[latest["risk_rank"] <= max(1, int(n * 0.01)), "risk_band"] = "top_1pct"

    forecast_date = (as_of + pd.Timedelta(days=1)).date()
    out = latest[["grid_id", "risk_score", "risk_rank", "risk_band"]].copy()
    out["forecast_date"] = pd.Timestamp(forecast_date)
    out = out[["grid_id", "forecast_date", "risk_score", "risk_rank", "risk_band"]]

    out_path = paths.outputs / f"risk_surface_{forecast_date}.parquet"
    out.to_parquet(out_path, index=False)
    return out
