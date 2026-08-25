with source as (
    select * from {{ source('silver', 'bods_services') }}
),

renamed as (
    select
        dataset_id,
        operator_noc,
        operator_name,
        service_code,
        line_name,
        origin,
        destination,
        start_date,
        end_date,
        days_of_week,
        scheduled_trips
    from source
    where operator_name is not null
      and line_name is not null
)

select * from renamed
