with source as (
    select * from {{ source('silver', 'ons_population') }}
),

renamed as (
    select
        la_code,
        la_name,
        geography_type,
        population_mid2024
    from source
    where la_code is not null
)

select * from renamed
