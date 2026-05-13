"""Sklearn pipeline + evaluation helpers for the repeat-purchase propensity model."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


def build_pipeline(
    model_type: str,
    numeric_features: list[str],
    categorical_features: list[str],
) -> Pipeline:
    """Build a sklearn Pipeline with preprocessing + classifier.

    model_type:
      'logreg' - LogisticRegression with class_weight='balanced'.
      'boost'  - HistGradientBoostingClassifier with class_weight='balanced'.
    """
    numeric_pipe = Pipeline(
        [
            ("impute", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
        ]
    )
    pre = ColumnTransformer(
        transformers=[
            ("num", numeric_pipe, numeric_features),
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), categorical_features),
        ],
        remainder="drop",
    )

    if model_type == "logreg":
        clf = LogisticRegression(class_weight="balanced", max_iter=1000, random_state=42)
    elif model_type == "boost":
        clf = HistGradientBoostingClassifier(
            max_iter=400,
            learning_rate=0.05,
            max_leaf_nodes=31,
            class_weight="balanced",
            random_state=42,
        )
    else:
        raise ValueError(f"Unknown model_type: {model_type!r}")

    return Pipeline([("pre", pre), ("clf", clf)])


def recall_at_top_k(y_true: np.ndarray, y_score: np.ndarray, top_frac: float = 0.10) -> float:
    """Recall when ranking by score and selecting the top `top_frac` of customers."""
    y_true = np.asarray(y_true)
    y_score = np.asarray(y_score)
    n_top = max(1, int(np.ceil(len(y_true) * top_frac)))
    order = np.argsort(y_score)[::-1]
    top_y = y_true[order[:n_top]]
    n_pos = int(y_true.sum())
    return float(top_y.sum() / n_pos) if n_pos else 0.0


def lift_at_top_k(y_true: np.ndarray, y_score: np.ndarray, top_frac: float = 0.10) -> float:
    """Precision in the top-k bucket divided by base rate."""
    y_true = np.asarray(y_true)
    base = y_true.mean()
    if base == 0:
        return 0.0
    n_top = max(1, int(np.ceil(len(y_true) * top_frac)))
    order = np.argsort(y_score)[::-1]
    top_precision = y_true[order[:n_top]].mean()
    return float(top_precision / base)


def evaluate(y_true: np.ndarray, y_score: np.ndarray) -> dict[str, float]:
    """Return all relevant metrics for an imbalanced binary classifier."""
    y_true = np.asarray(y_true)
    y_score = np.asarray(y_score)
    return {
        "n_samples": int(len(y_true)),
        "n_positives": int(y_true.sum()),
        "base_rate": float(y_true.mean()),
        "roc_auc": float(roc_auc_score(y_true, y_score)),
        "pr_auc": float(average_precision_score(y_true, y_score)),
        "brier": float(brier_score_loss(y_true, y_score)),
        "recall_top_10pct": recall_at_top_k(y_true, y_score, 0.10),
        "recall_top_20pct": recall_at_top_k(y_true, y_score, 0.20),
        "lift_top_10pct": lift_at_top_k(y_true, y_score, 0.10),
    }


def evaluate_df(results: dict[str, dict[str, float]]) -> pd.DataFrame:
    """Format a {model_name: metrics_dict} mapping as a comparison DataFrame."""
    return pd.DataFrame(results).round(4)
