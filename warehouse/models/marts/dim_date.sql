-- Grain: one row per calendar day, 2018-01-01 to 2027-12-31 -- covers the
-- fuel price series' full history plus the entire 2027 fare-cap year.
-- Self-contained generate_series spine; no dbt_utils dependency needed.
with date_spine as (
    select generate_series(
        '2018-01-01'::date, '2027-12-31'::date, interval '1 day'
    )::date as full_date
)

select
    to_char(full_date, 'YYYYMMDD')::int as date_key,
    full_date,
    extract(year from full_date)::smallint as year,
    extract(quarter from full_date)::smallint as quarter,
    extract(month from full_date)::smallint as month,
    trim(to_char(full_date, 'Month')) as month_name,
    trim(to_char(full_date, 'Day')) as day_of_week,
    case
        when extract(isodow from full_date) between 1 and 5 then 'Weekday'
        when extract(isodow from full_date) = 6 then 'Saturday'
        else 'Sunday'
    end as day_type,
    full_date >= '2027-01-01' as is_post_cap_period
from date_spine
