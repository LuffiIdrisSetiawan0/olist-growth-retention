"""Convert mart CSV exports to Parquet under api/data/ for production serving.

The API only needs the aggregate marts (small), not the detail tables (fct_orders, dim_customers).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
EXPORTS = ROOT / "data" / "exports"
API_DATA = ROOT / "api" / "data"

# Subset of marts that the API serves directly.
MARTS = [
    "monthly_revenue",
    "revenue_by_state",
    "customer_cohorts",
    "customer_rfm",
    "category_performance",
    "customer_clusters",
]


def main() -> int:
    API_DATA.mkdir(parents=True, exist_ok=True)
    print(f"Converting marts CSV -> Parquet in {API_DATA}\n")
    for mart in MARTS:
        src = EXPORTS / f"{mart}.csv"
        if not src.exists():
            print(f"  SKIP missing: {src.name}")
            continue
        df = pd.read_csv(src)
        out = API_DATA / f"{mart}.parquet"
        df.to_parquet(out, index=False)
        size_kb = out.stat().st_size / 1024
        print(f"  {mart:30s} {len(df):>8,} rows   {size_kb:>8,.1f} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
