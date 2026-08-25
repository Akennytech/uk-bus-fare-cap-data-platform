with source as (
    select * from {{ source('silver', 'fuel_prices_weekly') }}
),

renamed as (
    select
        week_start_date,
        petrol_pump_price_ppl,
        diesel_pump_price_ppl,
        petrol_duty_rate_ppl,
        diesel_duty_rate_ppl,
        petrol_vat_pct,
        diesel_vat_pct
    from source
    where week_start_date is not null
)

select * from renamed
