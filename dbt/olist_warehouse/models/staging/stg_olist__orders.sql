with source as (
    select * from {{ source('olist_raw', 'orders') }}
),

renamed as (
    select
        order_id,
        customer_id,
        order_status                        as status,
        order_purchase_timestamp            as purchased_at,
        order_approved_at                   as approved_at,
        order_delivered_carrier_date        as delivered_carrier_at,
        order_delivered_customer_date       as delivered_customer_at,
        order_estimated_delivery_date       as estimated_delivery_at,

        -- derived
        date(order_purchase_timestamp)      as purchased_date,
        timestamp_diff(order_delivered_customer_date, order_purchase_timestamp, day) as delivery_days,
        case
            when order_delivered_customer_date is null then null
            when order_delivered_customer_date > order_estimated_delivery_date then true
            else false
        end                                 as was_late
    from source
)

select * from renamed
