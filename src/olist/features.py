"""Feature engineering for the repeat-purchase propensity model.

All features are computed *as of a customer's first order* to avoid future leakage.
"""

from __future__ import annotations

import pandas as pd

FEATURE_COLUMNS_NUMERIC = [
    "delivery_days",
    "was_late",
    "avg_review_score",
    "item_count",
    "unique_products",
    "unique_sellers",
    "items_subtotal",
    "freight_total",
    "items_total",
    "max_installments",
    "payment_count",
    "payments_total",
    "first_order_month",
]

FEATURE_COLUMNS_CATEGORICAL = [
    "customer_state",
]


def first_order_features(fct_orders: pd.DataFrame) -> pd.DataFrame:
    """One row per customer_unique_id with first-order features only.

    Returns a DataFrame with: customer_unique_id, first_order_id, first_order_at,
    customer_state, plus all FEATURE_COLUMNS_NUMERIC.
    """
    df = fct_orders.copy()
    df["purchased_at"] = pd.to_datetime(df["purchased_at"])
    df = df.dropna(subset=["customer_unique_id"])
    df = df.sort_values(["customer_unique_id", "purchased_at"])
    first = df.groupby("customer_unique_id", as_index=False).first()

    keep = [
        "customer_unique_id",
        "order_id",
        "purchased_at",
        "customer_state",
        "delivery_days",
        "was_late",
        "avg_review_score",
        "item_count",
        "unique_products",
        "unique_sellers",
        "items_subtotal",
        "freight_total",
        "items_total",
        "max_installments",
        "payment_count",
        "payments_total",
    ]
    out = first[keep].rename(columns={"order_id": "first_order_id", "purchased_at": "first_order_at"})
    # Strip tz so downstream date comparisons against naive strings work uniformly.
    if out["first_order_at"].dt.tz is not None:
        out["first_order_at"] = out["first_order_at"].dt.tz_localize(None)
    out["first_order_month"] = out["first_order_at"].dt.month
    out["was_late"] = out["was_late"].eq(True).astype(int)
    return out


def add_repeat_target(
    features: pd.DataFrame,
    fct_orders: pd.DataFrame,
    horizon_days: int = 180,
) -> pd.DataFrame:
    """Add a binary target column 'repeat_within_<horizon>d'.

    Target = 1 if the customer placed a second order within `horizon_days` of their first.
    """
    fct = fct_orders.copy()
    fct["purchased_at"] = pd.to_datetime(fct["purchased_at"])

    second_at = (
        fct.sort_values(["customer_unique_id", "purchased_at"])
        .groupby("customer_unique_id")
        .nth(1)
        .reset_index()[["customer_unique_id", "purchased_at"]]
        .rename(columns={"purchased_at": "second_order_at"})
    )

    out = features.merge(second_at, on="customer_unique_id", how="left")
    out["second_order_at"] = pd.to_datetime(out["second_order_at"])
    if out["second_order_at"].dt.tz is not None:
        out["second_order_at"] = out["second_order_at"].dt.tz_localize(None)
    delta_days = (out["second_order_at"] - out["first_order_at"]).dt.days
    col = f"repeat_within_{horizon_days}d"
    out[col] = ((delta_days >= 0) & (delta_days <= horizon_days)).astype(int)
    return out


def chronological_split(
    features: pd.DataFrame,
    train_end: str,
    eval_end: str | None = None,
    date_col: str = "first_order_at",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split by first_order_at date.

    Train: rows with date_col < train_end.
    Test:  rows with train_end <= date_col <= eval_end (if eval_end given), else all later.

    For a model with horizon H, eval_end should be <= dataset_end - H to keep targets observable.
    """
    features = features.copy()
    features[date_col] = pd.to_datetime(features[date_col])
    train_end_ts = pd.Timestamp(train_end)
    train = features[features[date_col] < train_end_ts]
    rest = features[features[date_col] >= train_end_ts]
    if eval_end is not None:
        eval_end_ts = pd.Timestamp(eval_end)
        test = rest[rest[date_col] <= eval_end_ts]
    else:
        test = rest
    return train.reset_index(drop=True), test.reset_index(drop=True)
