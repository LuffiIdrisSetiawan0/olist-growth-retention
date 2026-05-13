-- Item-level aggregates per order (ephemeral, inlined into fct_orders).

select
    order_id,
    count(*)                            as item_count,
    count(distinct product_id)          as unique_products,
    count(distinct seller_id)           as unique_sellers,
    sum(price)                          as items_subtotal,
    sum(freight_value)                  as freight_total,
    sum(line_total)                     as items_total
from {{ ref('stg_olist__order_items') }}
group by order_id
