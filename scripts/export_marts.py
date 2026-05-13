"""Export dbt marts to CSV for Tableau Public ingestion.

Reads from BQ ecom_marts dataset, writes to data/exports/<mart>.csv.
Each CSV is idempotent (overwritten on re-run).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from google.cloud import bigquery

ROOT = Path(__file__).resolve().parent.parent
EXPORT_DIR = ROOT / "data" / "exports"

MARTS = [
    "monthly_revenue",
    "revenue_by_state",
    "customer_cohorts",
    "customer_rfm",
    "category_performance",
    "dim_customers",
    "dim_products",
    "fct_orders",
]


def main() -> int:
    load_dotenv()
    project = os.environ["GCP_PROJECT_ID"]
    marts_dataset = os.environ.get("BQ_DATASET_MARTS", "ecom_marts")
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    client = bigquery.Client(project=project)

    print(f"Exporting marts from {project}.{marts_dataset} to {EXPORT_DIR}\n")
    total_rows = 0
    for mart in MARTS:
        query = f"SELECT * FROM `{project}.{marts_dataset}.{mart}`"
        df = client.query(query).to_dataframe()
        out_path = EXPORT_DIR / f"{mart}.csv"
        df.to_csv(out_path, index=False)
        size_kb = out_path.stat().st_size / 1024
        print(f"  {mart:30s} {len(df):>8,} rows   {size_kb:>8,.1f} KB")
        total_rows += len(df)

    print(f"\nTotal: {total_rows:,} rows exported to {EXPORT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
