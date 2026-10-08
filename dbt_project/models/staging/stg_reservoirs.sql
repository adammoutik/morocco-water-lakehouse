-- staging view for raw reservoir measurements

with source_data as (
    select
        date::date as full_date,
        trim(lower(dam_id)) as dam_id,
        round(reserve_mm3::numeric, 4) as reserve_mm3,
        round(fill_pct::numeric, 4) as fill_pct
    from {{ source('staging', 'stg_reservoirs') }}
    where date is not null
      and dam_id is not null
)

select * from source_data
