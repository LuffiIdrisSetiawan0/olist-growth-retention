-- Products joined to the EN category translation.

with products as (
    select * from {{ ref('stg_olist__products') }}
),

translation as (
    select * from {{ ref('stg_olist__product_category_translation') }}
)

select
    p.product_id,
    p.category_name_pt,
    coalesce(t.category_name_en, p.category_name_pt, 'unknown') as category,
    p.name_length,
    p.description_length,
    p.photos_count,
    p.weight_g,
    p.length_cm,
    p.height_cm,
    p.width_cm
from products p
left join translation t on t.category_name_pt = p.category_name_pt
