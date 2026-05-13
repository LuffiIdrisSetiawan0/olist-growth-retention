-- Category × month revenue and order volume.

with items as (
    select * from {{ ref('stg_olist__order_items') }}
),

orders as (
    select * from {{ ref('fct_orders') }}
    where status not in ('canceled','unavailable')
),

products as (
    select * from {{ ref('dim_products') }}
)

select
    p.category,
    o.purchased_month                       as month,
    count(distinct o.order_id)              as orders,
    sum(i.price)                            as items_revenue,
    sum(i.freight_value)                    as freight_revenue,
    count(distinct i.product_id)            as unique_products_sold
from items i
join orders o   using (order_id)
join products p using (product_id)
group by p.category, o.purchased_month
order by p.category, o.purchased_month
