with source as (
    select * from {{ source('olist_raw', 'order_payments') }}
),

renamed as (
    select
        order_id,
        payment_sequential,
        payment_type,
        payment_installments as installments,
        payment_value
    from source
)

select * from renamed
