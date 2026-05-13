-- State-level revenue and customer breakdown.

with fct as (
    select * from {{ ref('fct_orders') }}
    where status not in ('canceled','unavailable')
)

select
    customer_state                                                          as state,
    count(distinct order_id)                                                as orders,
    count(distinct customer_unique_id)                                      as customers,
    sum(items_total)                                                        as gross_revenue,
    safe_divide(sum(items_total), count(distinct order_id))                 as avg_order_value,
    safe_divide(sum(items_total), count(distinct customer_unique_id))       as revenue_per_customer
from fct
group by customer_state
order by gross_revenue desc
