"""FastAPI app for the Olist portfolio demo.

Serves:
- JSON endpoints under /api/*
- Built React SPA from api/static/ at /
- /health for Hugging Face Spaces liveness checks.
"""

from __future__ import annotations

from collections import Counter
from contextlib import asynccontextmanager
from pathlib import Path

import numpy as np
import pandas as pd
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api import __version__
from api.data_loader import (
    load_model,
    load_model_meta,
    load_parquet,
    warm_cache,
)
from api.schemas import (
    CategoryResponse,
    CategoryRow,
    ClusterProfile,
    CohortCell,
    GeoResponse,
    HealthResponse,
    KpisResponse,
    ModelMetricsResponse,
    MonthlyRevenueRow,
    PredictRequest,
    PredictResponse,
    RetentionResponse,
    SegmentsResponse,
    StateRow,
)

STATIC_DIR = Path(__file__).resolve().parent / "static"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    warm_cache()
    yield


app = FastAPI(
    title="Olist Growth & Retention API",
    description="Public read-only API + ML predictor for the Olist Brazilian E-Commerce portfolio.",
    version=__version__,
    lifespan=lifespan,
)

# Vite dev server runs on :5173; production serves both from same origin so CORS is moot then.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse, tags=["meta"])
def health() -> HealthResponse:
    return HealthResponse(status="ok", version=__version__)


@app.get("/api/kpis", response_model=KpisResponse, tags=["analytics"])
def kpis() -> KpisResponse:
    df = load_parquet("monthly_revenue").copy()
    df["month"] = pd.to_datetime(df["month"]).dt.strftime("%Y-%m-%d")
    monthly = [
        MonthlyRevenueRow(
            month=str(row["month"]),
            orders=int(row["orders"]),
            customers=int(row["customers"]),
            gross_revenue=float(row["gross_revenue"]),
            items_revenue=float(row["items_revenue"]),
            freight_revenue=float(row["freight_revenue"]),
            avg_order_value=float(row["avg_order_value"]),
        )
        for _, row in df.iterrows()
    ]
    summary = {
        "total_orders": float(df["orders"].sum()),
        "total_customers": float(df["customers"].sum()),
        "total_gross_revenue": float(df["gross_revenue"].sum()),
        "avg_order_value": float(df["gross_revenue"].sum() / max(df["orders"].sum(), 1)),
        "months_covered": float(len(df)),
    }
    return KpisResponse(summary=summary, monthly=monthly)


@app.get("/api/retention", response_model=RetentionResponse, tags=["analytics"])
def retention() -> RetentionResponse:
    df = load_parquet("customer_cohorts").copy()
    df["cohort_month"] = pd.to_datetime(df["cohort_month"]).dt.strftime("%Y-%m-%d")
    cohorts = [
        CohortCell(
            cohort_month=str(row["cohort_month"]),
            months_since_first=int(row["months_since_first"]),
            active_customers=int(row["active_customers"]),
            cohort_size=int(row["cohort_size"]),
            retention_rate=float(row["retention_rate"]),
        )
        for _, row in df.iterrows()
    ]
    return RetentionResponse(cohorts=cohorts)


@app.get("/api/segments", response_model=SegmentsResponse, tags=["analytics"])
def segments() -> SegmentsResponse:
    rfm = load_parquet("customer_rfm")
    rule_based = dict(Counter(rfm["rfm_segment_label"].fillna("Unknown").tolist()))

    clusters_df = load_parquet("customer_clusters")
    merged = clusters_df.merge(
        rfm[["customer_unique_id", "recency_days", "frequency", "monetary"]],
        on="customer_unique_id",
        how="left",
    )
    grouped = (
        merged.groupby("cluster")
        .agg(
            n=("customer_unique_id", "count"),
            mean_recency_days=("recency_days", "mean"),
            mean_frequency=("frequency", "mean"),
            mean_monetary=("monetary", "mean"),
        )
        .reset_index()
        .sort_values("cluster")
    )
    kmeans = [
        ClusterProfile(
            cluster=str(row["cluster"]),
            n=int(row["n"]),
            mean_recency_days=float(row["mean_recency_days"]),
            mean_frequency=float(row["mean_frequency"]),
            mean_monetary=float(row["mean_monetary"]),
        )
        for _, row in grouped.iterrows()
    ]
    return SegmentsResponse(rule_based=rule_based, kmeans=kmeans)


@app.get("/api/geo", response_model=GeoResponse, tags=["analytics"])
def geo() -> GeoResponse:
    df = load_parquet("revenue_by_state")
    states = [
        StateRow(
            state=str(row["state"]),
            orders=int(row["orders"]),
            customers=int(row["customers"]),
            gross_revenue=float(row["gross_revenue"]),
            avg_order_value=float(row["avg_order_value"]),
            revenue_per_customer=float(row["revenue_per_customer"]),
        )
        for _, row in df.iterrows()
    ]
    return GeoResponse(states=states)


@app.get("/api/categories", response_model=CategoryResponse, tags=["analytics"])
def categories(limit: int = 20) -> CategoryResponse:
    df = load_parquet("category_performance")
    summed = (
        df.groupby("category")
        .agg(
            orders=("orders", "sum"),
            items_revenue=("items_revenue", "sum"),
            freight_revenue=("freight_revenue", "sum"),
            unique_products_sold=("unique_products_sold", "max"),
        )
        .reset_index()
        .sort_values("items_revenue", ascending=False)
        .head(limit)
    )
    top = [
        CategoryRow(
            category=str(row["category"]),
            orders=int(row["orders"]),
            items_revenue=float(row["items_revenue"]),
            freight_revenue=float(row["freight_revenue"]),
            unique_products_sold=int(row["unique_products_sold"]),
        )
        for _, row in summed.iterrows()
    ]
    return CategoryResponse(top=top)


@app.get("/api/model-metrics", response_model=ModelMetricsResponse, tags=["model"])
def model_metrics() -> ModelMetricsResponse:
    meta = load_model_meta()
    metrics = meta["metrics_test"]
    base_rate = float(next(iter(metrics.values()))["base_rate"])
    return ModelMetricsResponse(
        horizon_days=int(meta["horizon_days"]),
        train_size=int(meta["train_size"]),
        test_size=int(meta["test_size"]),
        base_rate=base_rate,
        metrics={k: {mk: float(mv) for mk, mv in v.items()} for k, v in metrics.items()},
        default_model=meta.get("default_model", "logreg"),
        top_features=[
            "max_installments",
            "unique_products",
            "payments_total",
            "item_count",
            "items_subtotal",
        ],
    )


@app.post("/api/predict-repeat-purchase", response_model=PredictResponse, tags=["model"])
def predict_repeat_purchase(req: PredictRequest) -> PredictResponse:
    meta = load_model_meta()
    model_name = f"repeat_purchase_{meta.get('default_model', 'logreg')}"
    pipe = load_model(model_name)

    feature_cols = meta["numeric_features"] + meta["categorical_features"]
    row = {col: getattr(req, col) for col in feature_cols}
    X = pd.DataFrame([row])

    proba = float(pipe.predict_proba(X)[0, 1])

    # Decile against the training distribution (approximation: load test predictions later).
    # For now, use the model's expected score range scaled to deciles.
    decile = int(np.clip(int(proba * 10) + 1, 1, 10))

    return PredictResponse(
        propensity=proba,
        decile=decile,
        model_version=model_name,
        horizon_days=int(meta["horizon_days"]),
    )


# ---------- Static React SPA ----------

if STATIC_DIR.exists():
    # Mounted in production where the React build is bundled into api/static.
    # Use a custom mount to allow client-side routing fallback to index.html.
    app.mount("/assets", StaticFiles(directory=str(STATIC_DIR / "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):  # noqa: ARG001
        index = STATIC_DIR / "index.html"
        return FileResponse(str(index))
