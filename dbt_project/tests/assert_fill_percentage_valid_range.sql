-- test: ensure fill percentage is between 0 and 105 percent

select
    fact_id,
    dam_id,
    full_date,
    fill_pct
from {{ ref('fact_reservoir_daily') }}
where fill_pct < 0
   or fill_pct > 105
