-- Dedupe ~1M raw rows to one row per zip prefix using average lat/lng.

with source as (
    select * from {{ source('olist_raw', 'geolocation') }}
),

aggregated as (
    select
        geolocation_zip_code_prefix     as zip_code_prefix,
        avg(geolocation_lat)            as latitude,
        avg(geolocation_lng)            as longitude,
        any_value(lower(geolocation_city))   as city,
        any_value(upper(geolocation_state))  as state
    from source
    group by geolocation_zip_code_prefix
)

select * from aggregated
