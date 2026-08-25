-- Grain: one row per (route, day-of-week pattern) as registered in BODS
-- timetable data -- NOT one row per calendar date. See ADR-005 in
-- documentation/data_dictionary.md: clean_bods.py counts VehicleJourney
-- elements per (operator, line, day-pattern), which tells you how much
-- service a route runs on e.g. a Monday-to-Friday pattern, not which exact
-- calendar dates it ran. date_key, weather_key, location_key, avg_fare and
-- delay_minutes from the original DDL are dropped here -- no source data
-- resolves them at this grain.

with base as (
    select
        operator_name,
        line_name,
        days_of_week,
        start_date,
        end_date,
        sum(scheduled_trips) as scheduled_trips
    from {{ ref('stg_bods_services') }}
    group by operator_name, line_name, days_of_week, start_date, end_date
),

with_keys as (
    select
        b.*,
        op.operator_key,
        rt.route_key
    from base b
    left join {{ ref('dim_operator') }} op
        on b.operator_name = op.operator_name
    left join {{ ref('dim_route') }} rt
        on b.line_name = rt.route_name
       and op.operator_key = rt.operator_key
),

with_fare_policy as (
    select
        wk.*,
        fp.fare_policy_key
    from with_keys wk
    left join {{ ref('dim_fare_policy') }} fp
        on wk.start_date::date >= fp.effective_from
       and (fp.effective_to is null or wk.start_date::date <= fp.effective_to)
)

select
    row_number() over (order by route_key, days_of_week) as fact_key,
    route_key,
    operator_key,
    fare_policy_key,
    days_of_week,
    start_date,
    end_date,
    scheduled_trips
from with_fare_policy
