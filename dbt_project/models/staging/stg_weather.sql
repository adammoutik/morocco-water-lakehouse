-- staging view for raw weather observations

with source_weather as (
    select
        date::date as full_date,
        trim(lower(location_id)) as location_id,
        trim(lower(location_type)) as location_type,
        round(precip_mm::numeric, 2) as precip_mm,
        round(max_temp_c::numeric, 2) as max_temp_c,
        round(min_temp_c::numeric, 2) as min_temp_c,
        round(latitude::numeric, 4) as latitude,
        round(longitude::numeric, 4) as longitude
    from {{ source('staging', 'stg_weather') }}
    where date is not null
      and location_id is not null
)

select * from source_weather
