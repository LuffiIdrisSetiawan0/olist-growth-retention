with source as (
    select * from {{ source('olist_raw', 'order_items') }}
),

renamed as (
    select
        order_id,
        order_item_id,
        product_id,
        seller_id,
        shipping_limit_date  as shipping_limit_at,
        price,
        freight_value,
        price + freight_value as line_total
    from source
)

select * from renamed
