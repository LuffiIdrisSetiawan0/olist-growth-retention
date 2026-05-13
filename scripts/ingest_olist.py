"""Download Olist Brazilian E-Commerce from Kaggle and load CSVs to BigQuery raw.

Idempotent: re-running skips Kaggle download if CSVs already exist, and overwrites
BQ tables (WRITE_TRUNCATE). Reads config from .env.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv
from google.cloud import bigquery

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"

TABLE_MAP = {
    "olist_customers_dataset.csv": "customers",
    "olist_geolocation_dataset.csv": "geolocation",
    "olist_order_items_dataset.csv": "order_items",
    "olist_order_payments_dataset.csv": "order_payments",
    "olist_order_reviews_dataset.csv": "order_reviews",
    "olist_orders_dataset.csv": "orders",
    "olist_products_dataset.csv": "products",
    "olist_sellers_dataset.csv": "sellers",
    "product_category_name_translation.csv": "product_category_translation",
}


def download_kaggle(slug: str, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    if all((dest / name).exists() for name in TABLE_MAP):
        print(f"All CSVs already present in {dest}, skipping Kaggle download.")
        return
    print(f"Downloading {slug} -> {dest}")
    subprocess.run(
        ["kaggle", "datasets", "download", "-d", slug, "-p", str(dest), "--unzip", "--force"],
        check=True,
    )


def ensure_dataset(client: bigquery.Client, dataset_id: str, location: str) -> None:
    ref = bigquery.Dataset(f"{client.project}.{dataset_id}")
    ref.location = location
    client.create_dataset(ref, exists_ok=True)
    print(f"Dataset ready: {client.project}.{dataset_id} ({location})")


def load_csv(client: bigquery.Client, csv_path: Path, dataset_id: str, table_name: str) -> int:
    table_id = f"{client.project}.{dataset_id}.{table_name}"
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.CSV,
        autodetect=True,
        skip_leading_rows=1,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        allow_quoted_newlines=True,
        max_bad_records=0,
    )
    with csv_path.open("rb") as f:
        job = client.load_table_from_file(f, table_id, job_config=job_config)
    job.result()
    return client.get_table(table_id).num_rows


def main() -> int:
    load_dotenv()
    project = os.environ["GCP_PROJECT_ID"]
    location = os.environ.get("BQ_LOCATION", "US")
    dataset_id = os.environ.get("BQ_DATASET_RAW", "ecom_raw")
    slug = os.environ.get("KAGGLE_DATASET", "olistbr/brazilian-ecommerce")

    download_kaggle(slug, RAW_DIR)

    client = bigquery.Client(project=project, location=location)
    ensure_dataset(client, dataset_id, location)

    print(f"\nLoading CSVs to {project}.{dataset_id}:")
    for csv_name, table_name in TABLE_MAP.items():
        csv_path = RAW_DIR / csv_name
        if not csv_path.exists():
            print(f"  SKIP missing: {csv_name}", file=sys.stderr)
            continue
        rows = load_csv(client, csv_path, dataset_id, table_name)
        print(f"  {table_name:35s} {rows:>10,} rows")

    print("\nIngestion complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
