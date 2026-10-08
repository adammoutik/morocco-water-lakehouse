-- date dimension table with calendar attributes and integer key

with distinct_dates as (
    select distinct full_date
    from {{ ref('stg_reservoirs') }}
    union
    select distinct full_date
    from {{ ref('stg_weather') }}
),

date_spine as (
    select
        full_date,
        -- Integer date key: 2026-08-01 -> 20260801
        to_char(full_date, 'YYYYMMDD')::integer as date_id,
        extract(year from full_date)::integer as year,
        extract(month from full_date)::integer as month,
        trim(to_char(full_date, 'Month')) as month_name,
        extract(day from full_date)::integer as day,
        extract(quarter from full_date)::integer as quarter,
        extract(isodow from full_date)::integer as day_of_week,
        trim(to_char(full_date, 'Day')) as day_name,
        case when extract(isodow from full_date) in (6, 7) then true else false end as is_weekend
    from distinct_dates
    where full_date is not null
)

select *
from date_spine
order by full_date
