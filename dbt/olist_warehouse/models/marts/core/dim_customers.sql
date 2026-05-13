-- One row per customer_unique_id (the actual person, NOT per-order customer_id).

with customers as (
    select * from {{ ref('stg_olist__customers') }}
),

orders as (
    select * from {{ ref('stg_olist__orders') }}
),

joined as (
    select
        c.customer_unique_id,
        c.customer_id,
        c.state,
        c.city,
        c.zip_code_prefix,
        o.order_id,
        o.purchased_at,
        o.status
    from customers c
    left join orders o on o.customer_id = c.customer_id
),

aggregated as (
    select
        customer_unique_id,
        any_value(state)                                                     as state,
        any_value(city)                                                      as city,
        any_value(zip_code_prefix)                                           as zip_code_prefix,
        count(distinct order_id)                                             as total_orders,
        count(distinct case when status = 'delivered' then order_id end)     as delivered_orders,
        count(distinct case when status = 'canceled' then order_id end)      as canceled_orders,
        min(purchased_at)                                                    as first_order_at,
        max(purchased_at)                                                    as last_order_at,
        date_diff(date(max(purchased_at)), date(min(purchased_at)), day)     as lifespan_days
    from joined
    group by customer_unique_id
)

select
    *,
    total_orders > 1 as is_repeat_buyer
from aggregated
