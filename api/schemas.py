"""Pydantic request/response schemas for the FastAPI app."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    status: Literal["ok"]
    version: str


# ---------- KPIs ----------


class MonthlyRevenueRow(BaseModel):
    month: str
    orders: int
    customers: int
    gross_revenue: float
    items_revenue: float
    freight_revenue: float
    avg_order_value: float


class KpisResponse(BaseModel):
    summary: dict[str, float]
    monthly: list[MonthlyRevenueRow]


# ---------- Retention ----------


class CohortCell(BaseModel):
    cohort_month: str
    months_since_first: int
    active_customers: int
    cohort_size: int
    retention_rate: float


class RetentionResponse(BaseModel):
    cohorts: list[CohortCell]


# ---------- Segments ----------


class ClusterProfile(BaseModel):
    cluster: str
    n: int
    mean_recency_days: float
    mean_frequency: float
    mean_monetary: float


class SegmentsResponse(BaseModel):
    rule_based: dict[str, int]
    kmeans: list[ClusterProfile]


# ---------- State / Category ----------


class StateRow(BaseModel):
    state: str
    orders: int
    customers: int
    gross_revenue: float
    avg_order_value: float
    revenue_per_customer: float


class GeoResponse(BaseModel):
    states: list[StateRow]


class CategoryRow(BaseModel):
    category: str
    orders: int
    items_revenue: float
    freight_revenue: float
    unique_products_sold: int


class CategoryResponse(BaseModel):
    top: list[CategoryRow]


# ---------- Model ----------


class ModelMetricsResponse(BaseModel):
    horizon_days: int
    train_size: int
    test_size: int
    base_rate: float
    metrics: dict[str, dict[str, float]]
    default_model: str
    top_features: list[str]


class PredictRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "items_total": 120.0,
            "items_subtotal": 100.0,
            "freight_total": 20.0,
            "payments_total": 120.0,
            "max_installments": 3,
            "payment_count": 1,
            "item_count": 1,
            "unique_products": 1,
            "unique_sellers": 1,
            "delivery_days": 10,
            "was_late": 0,
            "avg_review_score": 5.0,
            "first_order_month": 11,
            "customer_state": "SP",
        }
    })

    items_total: float = Field(..., gt=0)
    items_subtotal: float = Field(..., ge=0)
    freight_total: float = Field(0.0, ge=0)
    payments_total: float = Field(..., gt=0)
    max_installments: int = Field(1, ge=1, le=24)
    payment_count: int = Field(1, ge=1)
    item_count: int = Field(1, ge=1)
    unique_products: int = Field(1, ge=1)
    unique_sellers: int = Field(1, ge=1)
    delivery_days: float | None = Field(None, ge=0)
    was_late: int = Field(0, ge=0, le=1)
    avg_review_score: float | None = Field(None, ge=1, le=5)
    first_order_month: int = Field(..., ge=1, le=12)
    customer_state: str = Field("SP", min_length=2, max_length=2)


class PredictResponse(BaseModel):
    propensity: float = Field(..., description="Predicted probability that customer buys again within 180 days.")
    decile: int = Field(..., ge=1, le=10, description="Score decile (10 = top 10% most likely).")
    model_version: str
    horizon_days: int
