-- Monthly cohort retention table. Cohort = first purchase month per customer_unique_id.

with fct as (
    select * from {{ ref('fct_orders') }}
    where status not in ('canceled','unavailable')
),

first_purchase as (
    select
        customer_unique_id,
        date_trunc(min(purchased_date), month) as cohort_month
    from fct
    group by customer_unique_id
),

cohort_size as (
    select
        cohort_month,
        count(distinct customer_unique_id) as cohort_size
    from first_purchase
    group by cohort_month
),

orders_with_cohort as (
    select
        f.customer_unique_id,
        fp.cohort_month,
        date_trunc(f.purchased_date, month)                                          as activity_month,
        date_diff(date_trunc(f.purchased_date, month), fp.cohort_month, month)       as months_since_first
    from fct f
    join first_purchase fp using (customer_unique_id)
),

cohort_activity as (
    select
        cohort_month,
        months_since_first,
        count(distinct customer_unique_id) as active_customers
    from orders_with_cohort
    group by cohort_month, months_since_first
)

select
    a.cohort_month,
    s.cohort_size,
    a.months_since_first,
    a.active_customers,
    safe_divide(a.active_customers, s.cohort_size) as retention_rate
from cohort_activity a
join cohort_size s using (cohort_month)
order by cohort_month, months_since_first
