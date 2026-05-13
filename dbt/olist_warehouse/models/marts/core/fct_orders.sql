-- One row per order with line-item, payment, and review aggregates joined in.

with orders as (
    select * from {{ ref('stg_olist__orders') }}
),

customers as (
    select * from {{ ref('stg_olist__customers') }}
),

items as (
    select * from {{ ref('int_orders__item_totals') }}
),

payments as (
    select * from {{ ref('int_orders__payment_totals') }}
),

reviews as (
    select * from {{ ref('int_orders__review_aggregated') }}
)

select
    o.order_id,
    o.customer_id,
    c.customer_unique_id,
    c.state                                              as customer_state,
    o.status,
    o.purchased_at,
    o.purchased_date,
    date_trunc(o.purchased_date, month)                  as purchased_month,
    o.approved_at,
    o.delivered_customer_at,
    o.estimated_delivery_at,
    o.delivery_days,
    o.was_late,
    items.item_count,
    items.unique_products,
    items.unique_sellers,
    items.items_subtotal,
    items.freight_total,
    items.items_total,
    payments.payment_count,
    payments.max_installments,
    payments.payments_total,
    payments.payment_types,
    reviews.review_count,
    reviews.avg_score                                    as avg_review_score
from orders o
left join customers c on c.customer_id = o.customer_id
left join items     on items.order_id    = o.order_id
left join payments  on payments.order_id = o.order_id
left join reviews   on reviews.order_id  = o.order_id
