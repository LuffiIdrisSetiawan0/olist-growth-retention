-- Review aggregates per order (Olist has rare duplicate review rows per order).

select
    order_id,
    count(*)        as review_count,
    avg(score)      as avg_score,
    max(score)      as max_score,
    min(score)      as min_score
from {{ ref('stg_olist__order_reviews') }}
group by order_id
