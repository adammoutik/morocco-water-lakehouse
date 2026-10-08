-- test: ensure reserve volume is non-negative

select
    fact_id,
    dam_id,
    full_date,
    reserve_mm3
from {{ ref('fact_reservoir_daily') }}
where reserve_mm3 < 0
