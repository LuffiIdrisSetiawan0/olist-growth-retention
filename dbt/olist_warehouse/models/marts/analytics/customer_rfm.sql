-- RFM scoring per customer (customer_unique_id).
-- R: lower recency days = better → bucket 5 best.
-- F, M: higher = better → bucket 5 best.

with fct as (
    select * from {{ ref('fct_orders') }}
    where status not in ('canceled','unavailable')
),

snapshot as (
    select date_add(max(purchased_date), interval 1 day) as as_of from fct
),

per_customer as (
    select
        f.customer_unique_id,
        date_diff(s.as_of, max(f.purchased_date), day)               as recency_days,
        count(distinct f.order_id)                                   as frequency,
        sum(f.items_total)                                           as monetary
    from fct f, snapshot s
    group by f.customer_unique_id, s.as_of
),

scored as (
    select
        customer_unique_id,
        recency_days,
        frequency,
        monetary,
        ntile(5) over (order by recency_days desc) as r_score,
        ntile(5) over (order by frequency asc)     as f_score,
        ntile(5) over (order by monetary asc)      as m_score
    from per_customer
)

select
    *,
    concat(cast(r_score as string), cast(f_score as string), cast(m_score as string)) as rfm_segment_code,
    case
        when r_score >= 4 and f_score >= 4 and m_score >= 4 then 'Champions'
        when r_score >= 3 and f_score >= 3 and m_score >= 3 then 'Loyal'
        when r_score >= 4 and f_score <= 2                  then 'New'
        when r_score <= 2 and f_score >= 3                  then 'At Risk'
        when r_score <= 2 and f_score <= 2                  then 'Lost'
        else 'Other'
    end as rfm_segment_label
from scored
