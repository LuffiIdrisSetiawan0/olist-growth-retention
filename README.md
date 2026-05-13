# Olist E-Commerce — Growth & Retention Portfolio

Hybrid **Data Analyst + Data Scientist** portfolio project on the [Olist Brazilian E-Commerce dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) (2016–2018). Covers an end-to-end analytics stack: ingestion → warehouse modeling → BI dashboard → ML segmentation & propensity → public demo app.

Runs **fully on free tiers** — no billing account required anywhere.

## Status

| Phase | Scope | Status |
| --- | --- | --- |
| Fase 1 | Ingest → dbt → Tableau Public dashboard | dbt pipeline complete; dashboard authoring pending |
| **Fase 2** | RFM + KMeans + repeat-purchase model | notebooks + saved model |
| Fase 3 | FastAPI + React on Hugging Face Spaces | not started |

## Stack

| Layer | Tool |
| --- | --- |
| Data warehouse (dev) | BigQuery Sandbox |
| SQL transforms + tests | dbt-bigquery |
| Pipeline scripts | Python 3.11 + uv |
| BI dashboard | Tableau Public |
| Serving (Fase 3) | DuckDB + Parquet inside Docker |
| API (Fase 3) | FastAPI |
| Frontend (Fase 3) | React + Vite + TypeScript |
| Public demo (Fase 3) | Hugging Face Spaces (Docker SDK) |
| CI | GitHub Actions |

## Repo layout

```
.
├── data/
│   ├── raw/         # Olist CSVs from Kaggle (gitignored)
│   └── exports/     # Mart CSVs for Tableau (gitignored)
├── dbt/olist_warehouse/
│   ├── models/
│   │   ├── staging/        # 9 typed views over raw
│   │   ├── intermediate/   # 3 ephemeral aggregates
│   │   └── marts/
│   │       ├── core/       # dim_customers, dim_products, fct_orders
│   │       └── analytics/  # monthly_revenue, customer_rfm, customer_cohorts, revenue_by_state, category_performance
│   ├── macros/
│   ├── packages.yml
│   ├── profiles.yml         # gitignored
│   └── profiles.example.yml
├── scripts/
│   ├── ingest_olist.py     # Kaggle → BigQuery raw
│   └── export_marts.py     # BigQuery marts → CSV for Tableau
├── notebooks/               # Fase 2 (EDA, model dev)
├── src/olist/               # reusable helpers
├── reports/                 # Tableau screenshots, narrative
├── api/                     # FastAPI app (Fase 3)
└── web/                     # React app (Fase 3)
```

## Setup — reproduce from scratch

Prereqs: Python 3.11, [uv](https://docs.astral.sh/uv/), Git, Node 20+ (Fase 3), Docker (Fase 3), `gcloud` SDK, Kaggle CLI with `~/.kaggle/kaggle.json`.

```powershell
# 1. Install Python deps
uv sync --all-groups

# 2. Copy env template and set your GCP project id
Copy-Item .env.example .env
# edit .env: GCP_PROJECT_ID=<your-bq-sandbox-project-id>

# 3. Auth to BigQuery (browser opens once)
gcloud auth login --update-adc
gcloud config set project <your-project-id>
gcloud auth application-default set-quota-project <your-project-id>

# 4. Ingest Olist (~100MB Kaggle download, ~30s BQ load)
uv run python scripts/ingest_olist.py

# 5. Build the warehouse + run tests
uv run dbt deps  --project-dir dbt/olist_warehouse --profiles-dir dbt/olist_warehouse
uv run dbt build --project-dir dbt/olist_warehouse --profiles-dir dbt/olist_warehouse

# 6. Export marts to CSV for Tableau Public
uv run python scripts/export_marts.py
```

## Fase 1 results

**Raw** (`ecom_raw`, 9 tables loaded from CSV):

| Table | Rows |
| --- | --- |
| orders | 99,441 |
| customers | 99,441 |
| order_items | 112,650 |
| order_payments | 103,886 |
| order_reviews | 99,224 |
| products | 32,951 |
| sellers | 3,095 |
| geolocation | 1,000,163 |
| product_category_translation | 71 |

**Marts** (`ecom_marts`, materialized as tables):

| Mart | Rows | Purpose |
| --- | --- | --- |
| dim_customers | 96,096 | Unique customers (by `customer_unique_id`) |
| dim_products | 32,951 | Products joined to EN category translation |
| fct_orders | 99,441 | One row per order with item/payment/review aggregates |
| monthly_revenue | 24 | Executive KPI overview |
| customer_rfm | 94,990 | RFM scores + segment label per customer |
| customer_cohorts | 220 | Cohort × months_since_first retention table |
| revenue_by_state | 27 | All Brazilian states |
| category_performance | 1,282 | Category × month |

**Test summary:** 79 PASS, 1 WARN (known duplicate `review_id` in source data), 0 ERROR across 80 tests.

## Methodology notes

- **Customer identity:** Olist has two customer IDs. `customer_id` is per-order (rotates on each order); `customer_unique_id` is the actual person. All cohort, RFM, and dim_customers logic uses `customer_unique_id`. Using the wrong one silently breaks every retention metric.
- **Repeat-purchase rate ≈ 3%.** 99,441 orders come from 96,096 unique customers → about 3,345 customers (3.5%) have more than one order. Class imbalance dictates that **PR-AUC and recall@top-decile** will be the headline metrics in Fase 2, not ROC-AUC.
- **Cohort right-censoring:** the dataset window is ~24 months (2016-09 to 2018-10). Cohorts after April 2018 have less than 6 months of follow-up; retention curves should be read with this in mind.
- **Reviews in Portuguese.** Skipped from NLP scope; review scores (1–5) are used as-is.
- **Geolocation deduplication:** the raw `geolocation` table has 1M rows with duplicates per zip prefix. The staging model collapses to one row per zip prefix using `AVG(lat/lng)` and `ANY_VALUE(city/state)`.
- **Delivery delay flag:** `was_late = delivered_customer_at > estimated_delivery_at`. Derived in staging; not present in the raw schema.

## Building the Tableau Public dashboard

After running `uv run python scripts/export_marts.py`, the CSVs in `data/exports/` are the data source for Tableau Public Desktop.

1. **Open Tableau Public Desktop → Connect → Text File.**
2. Add each CSV individually as a data source (or connect once and use the "Add Connection" flow to relate them).
3. Suggested relationships (drag-link in the data model):
   - `fct_orders.customer_unique_id` ↔ `dim_customers.customer_unique_id`
   - `fct_orders.order_id` ↔ `category_performance` via custom calculation if needed (or use `category_performance` standalone)
   - `customer_rfm.customer_unique_id` ↔ `dim_customers.customer_unique_id`
4. Build worksheets:
   - **Executive KPI overview** — line chart from `monthly_revenue` (revenue, orders, AOV by month).
   - **Cohort retention heatmap** — from `customer_cohorts`: rows = `cohort_month`, columns = `months_since_first`, color = `retention_rate`.
   - **RFM segment counts** — bar chart from `customer_rfm` grouped by `rfm_segment_label`.
   - **State revenue map** — symbol map from `revenue_by_state` using state code (BR-XX) or filled map by state name.
   - **Top categories** — horizontal bar from `category_performance` aggregated by `category`.
5. Assemble worksheets into 1-2 dashboards and a story.
6. **File → Save to Tableau Public As…** → fill metadata → publish. Copy the resulting URL into this README.

> Live dashboard: _coming soon — link will be added here once published._

## CI

[`.github/workflows/ci.yml`](.github/workflows/ci.yml) runs on every push and PR:

- `ruff check .` for Python lint
- `dbt deps` + `dbt parse --target ci` (DuckDB profile, no DB connection needed) for dbt validation

Local equivalent:

```powershell
uv run ruff check .
uv run dbt parse --project-dir dbt/olist_warehouse --profiles-dir dbt/olist_warehouse --target ci
```

## Limitations

- Olist data is historical (2016-09 to 2018-10); the project demonstrates methodology, not current market claims.
- BigQuery Sandbox tables expire after 60 days by default. Re-run `uv run python scripts/ingest_olist.py` and `uv run dbt build` to refresh.
- Tableau Public hosts dashboards publicly and does not support live BigQuery connections on free accounts — that's why we export CSV snapshots instead.

## Fase 2 results

Three notebooks in [`notebooks/`](notebooks/), written as `.py` with `# %%` cell markers (open in VS Code Jupyter or JupyterLab via jupytext):

- [`01_eda.py`](notebooks/01_eda.py) — repeat-rate validation, cohort right-censoring, RFM segment distribution, geographic and delivery-time distributions.
- [`02_segmentation.py`](notebooks/02_segmentation.py) — KMeans on log-transformed RFM, k chosen by elbow + silhouette (`k = 4`), cluster profiles, cross-tab vs rule-based labels.
- [`03_repeat_purchase.py`](notebooks/03_repeat_purchase.py) — propensity model with chronological split, two model comparison, PR/calibration curves, permutation importance, pickled artifacts.

**Propensity model — test set (24,760 customers, 2.84% base rate):**

| Metric | Logistic Regression | HistGradientBoosting |
| --- | --- | --- |
| PR-AUC | **0.0394** | 0.0358 |
| Recall @ top-10% | **17.5%** | 16.5% |
| Lift @ top-10% | **1.75×** | 1.65× |
| ROC-AUC | 0.572 | 0.540 |
| Brier score | 0.262 | **0.232** |

**Honest read.** With ~3% positive class, the linear baseline edges out the boosted model on ranking metrics — `class_weight='balanced'` on HGBT trades calibration for recall in a way that hurts precision in the top decile. Top features by permutation importance: `max_installments`, `unique_products`, `payments_total`. `delivery_days`, `was_late`, and `customer_state` did not provide useful signal in this configuration.

Both models are saved as pickles under [`models/`](models/) along with `repeat_purchase.meta.json` (training metadata + metrics). `default_model = "logreg"` reflects the PR-AUC winner.

KMeans clusters (saved to `data/exports/customer_clusters.csv`):

| Cluster | n | mean recency | mean frequency | mean monetary | description |
| --- | --- | --- | --- | --- | --- |
| C0 | 28,387 | 180d | 1.00 | 318.72 | Recent high-value first-timers |
| C1 | 2,888 | 227d | 2.11 | 308.26 | Repeat buyers — target for retention |
| C2 | 27,450 | 432d | 1.00 | 119.92 | Old single buyers — lost / at risk |
| C3 | 36,258 | 154d | 1.00 | 69.12 | Recent low-value first-timers |

Figures: [`reports/figures/`](reports/figures/) holds all 11 PNGs referenced by the notebooks (cohort heatmap, RFM segments, KMeans elbow + 2D scatter, train/test split, PR curves, calibration, permutation importance).

## Roadmap

- [x] **Fase 1 — DA piece.** Ingest Olist → dbt staging + marts → CSV exports → CI. *(Tableau dashboard authoring is the remaining manual step.)*
- [x] **Fase 2 — DS layer.** EDA, RFM + KMeans segmentation, repeat-purchase propensity model with chronological split, comparison + calibration + permutation importance.
- [ ] **Fase 3 — Engineering layer.** FastAPI + React demo, Docker container, deploy to Hugging Face Spaces.

## License

MIT — see [LICENSE](LICENSE).
