with source as (
    select * from {{ source('silver', 'imd_la_summary') }}
),

renamed as (
    select
        la_code,
        la_name as district_name,
        num_lsoas,
        avg_imd_score,
        avg_imd_rank,
        avg_imd_decile,
        avg_income_decile,
        avg_employment_decile,
        total_population_mid2015
    from source
    where la_code is not null
)

select * from renamed
