"""Load parquet marts and pickled ML models. Cached for the process lifetime."""

from __future__ import annotations

import json
import pickle
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd

API_DIR = Path(__file__).resolve().parent
DATA_DIR = API_DIR / "data"
MODELS_DIR = API_DIR.parent / "models"


@lru_cache(maxsize=None)
def load_parquet(name: str) -> pd.DataFrame:
    path = DATA_DIR / f"{name}.parquet"
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run `uv run python scripts/build_serving_data.py` first."
        )
    return pd.read_parquet(path)


@lru_cache(maxsize=None)
def load_model(name: str = "repeat_purchase_logreg") -> Any:
    path = MODELS_DIR / f"{name}.pkl"
    if not path.exists():
        raise FileNotFoundError(f"{path} not found. Re-run notebooks/03_repeat_purchase.py.")
    with path.open("rb") as f:
        return pickle.load(f)


@lru_cache(maxsize=None)
def load_model_meta() -> dict[str, Any]:
    path = MODELS_DIR / "repeat_purchase.meta.json"
    if not path.exists():
        raise FileNotFoundError(f"{path} not found. Re-run notebooks/03_repeat_purchase.py.")
    return json.loads(path.read_text())


def warm_cache() -> None:
    """Touch all data + model artifacts at startup to fail fast if anything is missing."""
    for mart in [
        "monthly_revenue",
        "revenue_by_state",
        "customer_cohorts",
        "customer_rfm",
        "category_performance",
        "customer_clusters",
    ]:
        load_parquet(mart)
    load_model_meta()
    load_model("repeat_purchase_logreg")
