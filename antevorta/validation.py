from __future__ import annotations

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import KFold

from antevorta.config import CONFIG
from antevorta.model import TrainingData


def validate_model(data: TrainingData, kfold: int, seed: int = CONFIG.seed) -> dict[str, float]:
    if kfold < 2:
        raise ValueError("kfold must be >= 2")
    if len(data.x) < kfold:
        raise ValueError("kfold cannot exceed number of samples")

    splitter = KFold(n_splits=kfold, shuffle=True, random_state=seed)
    scores: list[float] = []

    for train_idx, test_idx in splitter.split(data.x):
        x_train = data.x.iloc[train_idx]
        y_train = data.y.iloc[train_idx]
        x_test = data.x.iloc[test_idx]
        y_test = data.y.iloc[test_idx]

        if y_train.nunique() < 2 or y_test.nunique() < 2:
            raise ValueError("Each fold must contain both classes; adjust kfold or data")

        model = LogisticRegression(
            penalty="l2",
            solver="lbfgs",
            random_state=seed,
            max_iter=1000,
        )
        model.fit(x_train, y_train)
        preds = model.predict_proba(x_test)[:, 1]
        scores.append(float(roc_auc_score(y_test, preds)))

    scores_arr = np.array(scores, dtype=float)
    return {
        "kfold": float(kfold),
        "auc_mean": float(scores_arr.mean()),
        "auc_std": float(scores_arr.std(ddof=0)),
    }
