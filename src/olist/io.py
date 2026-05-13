"""Data loading helpers — read marts from BigQuery or local CSV exports."""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from google.cloud import bigquery

ROOT = Path(__file__).resolve().parent.parent.parent
EXPORTS_DIR = ROOT / "data" / "exports"


def load_env() -> None:
    """Load .env from the project root (idempotent)."""
    load_dotenv(ROOT / ".env", override=False)


def bq_client() -> bigquery.Client:
    """Return a BigQuery client using GCP_PROJECT_ID from .env."""
    load_env()
    return bigquery.Client(project=os.environ["GCP_PROJECT_ID"])


def read_mart(name: str, source: str = "csv") -> pd.DataFrame:
    """Load a mart by name.

    Parameters
    ----------
    name : str
        Mart table name (e.g., 'fct_orders', 'customer_rfm').
    source : {'csv', 'bigquery'}
        'csv' (default): read from data/exports/<name>.csv (fast, offline).
        'bigquery': query the BQ table directly (always fresh, needs ADC).
    """
    if source == "csv":
        path = EXPORTS_DIR / f"{name}.csv"
        if not path.exists():
            raise FileNotFoundError(
                f"{path} not found. Run `uv run python scripts/export_marts.py` first."
            )
        return pd.read_csv(path)
    if source == "bigquery":
        load_env()
        project = os.environ["GCP_PROJECT_ID"]
        dataset = os.environ.get("BQ_DATASET_MARTS", "ecom_marts")
        client = bq_client()
        return client.query(f"SELECT * FROM `{project}.{dataset}.{name}`").to_dataframe()
    raise ValueError(f"Unknown source: {source!r}. Use 'csv' or 'bigquery'.")
