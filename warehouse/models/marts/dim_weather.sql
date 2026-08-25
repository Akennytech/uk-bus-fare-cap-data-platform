-- Grain: one row per (city, date). city maps directly onto three of
-- dim_location's six areas (Derby, Leicester, Nottingham), since Open-Meteo
-- was queried at those exact city centroids.
with weather as (
    select
        city,
        observation_date,
        mean_temp_c,
        precipitation_mm,
        windspeed_max_kmh,
        case when precipitation_mm > 0.2 then 'Wet' else 'Dry' end as condition
    from {{ ref('stg_weather_daily') }}
)

select
    row_number() over (order by w.city, w.observation_date) as weather_key,
    w.observation_date,
    loc.la_code,
    w.mean_temp_c,
    w.precipitation_mm,
    w.windspeed_max_kmh,
    w.condition
from weather w
left join {{ ref('dim_location') }} loc
    on w.city = loc.la_name
