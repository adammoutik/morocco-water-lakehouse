-- dimension table for reservoirs with static metadata and capacities

with distinct_dams as (
    select distinct dam_id
    from {{ ref('stg_reservoirs') }}
),

dam_metadata as (
    select
        dam_id,
        case dam_id
            when 'yacoub_el_mansour' then 'Yacoub El Mansour'
            when 'lalla_takerkoust' then 'Lalla Takerkoust'
            when 'abou_el_abess_sebti' then 'Abou El Abess Sebti'
            when 'sd_mohamed_ben_slimane_el_jazouli' then 'Sidi Mohamed Ben Slimane El Jazouli'
            when 'bge_my_abdrhmane' then 'BGE Moulay Abderrahmane'
            else initcap(replace(dam_id, '_', ' '))
        end as display_name,
        case dam_id
            when 'yacoub_el_mansour' then 'High Atlas'
            when 'lalla_takerkoust' then 'Haouz plain'
            when 'abou_el_abess_sebti' then 'High Atlas'
            when 'sd_mohamed_ben_slimane_el_jazouli' then 'Western Tensift'
            when 'bge_my_abdrhmane' then 'High Atlas foothills'
            else 'Tensift basin'
        end as region,
        -- Normal reservoir design capacity (Capacité Normale in Million m3) from official agency bulletins
        case dam_id
            when 'yacoub_el_mansour' then 57.45
            when 'lalla_takerkoust' then 50.82
            when 'abou_el_abess_sebti' then 22.37
            when 'sd_mohamed_ben_slimane_el_jazouli' then 12.31
            when 'bge_my_abdrhmane' then 58.99
            else null
        end::numeric(10, 2) as capacity_mm3,
        case dam_id
            when 'yacoub_el_mansour' then 31.1899
            when 'lalla_takerkoust' then 31.3548
            when 'abou_el_abess_sebti' then 31.1400
            when 'sd_mohamed_ben_slimane_el_jazouli' then 31.2500
            when 'bge_my_abdrhmane' then 31.1000
            else null
        end::numeric(8, 4) as latitude,
        case dam_id
            when 'yacoub_el_mansour' then -8.0882
            when 'lalla_takerkoust' then -8.1360
            when 'abou_el_abess_sebti' then -8.3100
            when 'sd_mohamed_ben_slimane_el_jazouli' then -9.1800
            when 'bge_my_abdrhmane' then -8.7600
            else null
        end::numeric(8, 4) as longitude,
        'Tensift' as basin_name
    from distinct_dams
)

select
    -- Deterministic surrogate key (MD5 hash)
    md5(dam_id) as reservoir_id,
    dam_id,
    display_name,
    region,
    basin_name,
    capacity_mm3,
    latitude,
    longitude
from dam_metadata
