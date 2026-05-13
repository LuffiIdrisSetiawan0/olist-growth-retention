with source as (
    select * from {{ source('olist_raw', 'products') }}
),

renamed as (
    select
        product_id,
        product_category_name        as category_name_pt,
        product_name_lenght          as name_length,
        product_description_lenght   as description_length,
        product_photos_qty           as photos_count,
        product_weight_g             as weight_g,
        product_length_cm            as length_cm,
        product_height_cm            as height_cm,
        product_width_cm             as width_cm
    from source
)

select * from renamed
