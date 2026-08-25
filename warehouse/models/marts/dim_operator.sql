-- Grain: one row per distinct bus operator seen in BODS timetable data.
with operators as (
    select
        operator_name,
        max(operator_noc) as operator_noc
    from {{ ref('stg_bods_services') }}
    where operator_name is not null
    group by operator_name
)

select
    row_number() over (order by operator_name) as operator_key,
    operator_noc as operator_id,
    operator_name,
    'East Midlands' as region
from operators
order by operator_name
