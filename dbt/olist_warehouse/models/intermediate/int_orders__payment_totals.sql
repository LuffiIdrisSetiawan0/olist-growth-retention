-- Payment aggregates per order. An order can have multiple payment lines.

select
    order_id,
    count(*)                                                            as payment_count,
    max(installments)                                                   as max_installments,
    sum(payment_value)                                                  as payments_total,
    string_agg(distinct payment_type order by payment_type)             as payment_types
from {{ ref('stg_olist__order_payments') }}
group by order_id
