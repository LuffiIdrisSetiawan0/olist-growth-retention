-- Source columns auto-named string_field_0/1 by BQ autodetect (header looked like data).

with source as (
    select * from {{ source('olist_raw', 'product_category_translation') }}
),

renamed as (
    select
        string_field_0 as category_name_pt,
        string_field_1 as category_name_en
    from source
)

select * from renamed
