-- Month-level KPIs: orders, customers, GMV, AOV.

with fct as (
    select * from {{ ref('fct_orders') }}
    where status not in ('canceled','unavailable')
)

select
    purchased_month                                              as month,
    count(distinct order_id)                                     as orders,
    count(distinct customer_unique_id)                           as customers,
    sum(items_total)                                             as gross_revenue,
    sum(items_subtotal)                                          as items_revenue,
    sum(freight_total)                                           as freight_revenue,
    safe_divide(sum(items_total), count(distinct order_id))      as avg_order_value
from fct
group by purchased_month
order by purchased_month
