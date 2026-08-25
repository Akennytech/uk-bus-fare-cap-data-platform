with source as (
    select * from {{ source('silver', 'weather_daily') }}
),

renamed as (
    select
        city,
        date as observation_date,
        temp_max_c,
        temp_min_c,
        round((temp_max_c + temp_min_c) / 2.0, 1) as mean_temp_c,
        precipitation_mm,
        windspeed_max_kmh
    from source
    where date is not null
)

select * from renamed
