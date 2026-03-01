from __future__ import annotations

import pandas as pd

from antevorta.model import TrainingData
from antevorta.validation import validate_model


def test_validation_metrics_are_deterministic():
    x = pd.DataFrame(
        {
            "factor_a": [0.1, 0.2, 0.9, 1.0, 0.15, 0.95],
            "factor_b": [1.0, 0.8, 0.2, 0.1, 0.9, 0.05],
        }
    )
    y = pd.Series([0, 0, 1, 1, 0, 1], name="label")

    metrics_1 = validate_model(TrainingData(x=x, y=y), kfold=3, seed=42)
    metrics_2 = validate_model(TrainingData(x=x, y=y), kfold=3, seed=42)

    assert metrics_1 == metrics_2
    assert 0.0 <= metrics_1["auc_mean"] <= 1.0
    assert metrics_1["auc_std"] >= 0.0
