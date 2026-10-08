-- fact table for daily reservoir metrics and weather conditions

with reservoirs as (
    select
        full_date,
        dam_id,
        reserve_mm3,
        fill_pct
    from {{ ref('stg_reservoirs') }}
),

dim_res as (
    select
        reservoir_id,
        dam_id
    from {{ ref('dim_reservoir') }}
),

dim_dt as (
    select
        date_id,
        full_date
    from {{ ref('dim_date') }}
),

local_weather as (
    select
        full_date,
        location_id as dam_id,
        precip_mm,
        max_temp_c,
        min_temp_c
    from {{ ref('stg_weather') }}
    where location_type != 'basin'
),

basin_weather as (
    select
        full_date,
        precip_mm as precip_mm_basin,
        max_temp_c as max_temp_c_basin,
        min_temp_c as min_temp_c_basin
    from {{ ref('stg_weather') }}
    where location_id = 'tensift_basin' or location_type = 'basin'
),

joined_facts as (
    select
        -- Surrogate Key for the Fact Record
        md5(concat(r.dam_id, '_', r.full_date::text)) as fact_id,
        
        -- Dimension Foreign Keys
        d.date_id,
        dr.reservoir_id,

        -- Degenerate Dimensions (Useful for debugging and quick filtering)
        r.full_date,
        r.dam_id,

        -- Quantitative Reservoir Metrics
        r.reserve_mm3,
        r.fill_pct,

        -- Daily Drawdown Metric: Today's reserve minus Yesterday's reserve
        -- Negative value = water depletion/usage; Positive value = inflow/refill
        round((r.reserve_mm3 - lag(r.reserve_mm3) over (
            partition by r.dam_id order by r.full_date
        ))::numeric, 4) as delta_reserve_mm3,

        -- Meteorological Metrics (with fallback to basin rainfall if local station is null)
        coalesce(lw.precip_mm, bw.precip_mm_basin) as precip_mm,
        bw.precip_mm_basin,
        coalesce(lw.max_temp_c, bw.max_temp_c_basin) as max_temp_c,
        coalesce(lw.min_temp_c, bw.min_temp_c_basin) as min_temp_c

    from reservoirs r
    inner join dim_res dr
        on r.dam_id = dr.dam_id
    inner join dim_dt d
        on r.full_date = d.full_date
    left join local_weather lw
        on r.full_date = lw.full_date
       and r.dam_id = lw.dam_id
    left join basin_weather bw
        on r.full_date = bw.full_date
)

select *
from joined_facts
order by dam_id, full_date
