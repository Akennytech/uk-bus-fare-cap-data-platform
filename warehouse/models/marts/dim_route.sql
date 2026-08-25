-- Grain: one row per (operator, line) combination seen in BODS timetable
-- data. route_type is not populated -- no reliable source classifies
-- routes as Urban/Rural/Coastal/Interurban in the data we have; left NULL
-- rather than guessed.
with route_base as (
    select
        operator_name,
        line_name,
        min(service_code) as route_id
    from {{ ref('stg_bods_services') }}
    where operator_name is not null
      and line_name is not null
    group by operator_name, line_name
)

select
    row_number() over (order by rb.line_name, rb.route_id) as route_key,
    rb.route_id,
    rb.line_name as route_name,
    op.operator_key,
    cast(null as varchar) as route_type
from route_base rb
left join {{ ref('dim_operator') }} op
    on rb.operator_name = op.operator_name
