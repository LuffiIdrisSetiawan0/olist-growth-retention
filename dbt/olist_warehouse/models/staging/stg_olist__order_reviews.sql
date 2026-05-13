with source as (
    select * from {{ source('olist_raw', 'order_reviews') }}
),

renamed as (
    select
        review_id,
        order_id,
        review_score             as score,
        review_comment_title     as comment_title,
        review_comment_message   as comment_message,
        review_creation_date     as created_at,
        review_answer_timestamp  as answered_at
    from source
)

select * from renamed
