-- Grain: one row per (location, household_type) -- a static pre-cap vs
-- post-cap comparison, not a monthly time series. Deviates from the
-- original DDL's "per month" grain description: no source data in this
-- project varies these assumptions by month (journeys/week and the cap
-- amount are both flat within a policy period), so a literal per-month
-- grain would just repeat identical rows 12x with no analytical value.
-- See ADR-006 in documentation/data_dictionary.md.
--
-- Compares the GBP3 cap (the policy in effect immediately before the
-- change) against the GBP2 cap (2027) -- the actual before/after this
-- project analyzes. Every fare-capped journey is assumed to actually hit
-- the cap amount -- a simplification, documented in assumption_notes on
-- every row.

with pre_cap as (
    select cap_amount from {{ ref('dim_fare_policy') }} where period_name = 'GBP3 cap'
),
post_cap as (
    select cap_amount from {{ ref('dim_fare_policy') }} where period_name = 'GBP2 cap (2027)'
)

select
    row_number() over (order by loc.location_key, hh.household_type) as fact_key,
    loc.location_key,
    hh.household_type,
    round(hh.weekly_bus_journeys * pre_cap.cap_amount, 2) as weekly_cost_pre_cap,
    round(hh.weekly_bus_journeys * post_cap.cap_amount, 2) as weekly_cost_post_cap,
    round(
        (hh.weekly_bus_journeys * pre_cap.cap_amount - hh.weekly_bus_journeys * post_cap.cap_amount) * 52,
        2
    ) as est_annual_saving,
    hh.weekly_bus_journeys || ' journeys/week assumed (' || hh.notes || '). Compares GBP3 cap vs GBP2 cap (2027); every fare-capped journey assumed to hit the cap amount exactly -- a simplification.' as assumption_notes
from {{ ref('dim_location') }} loc
cross join {{ ref('household_travel_assumptions') }} hh
cross join pre_cap
cross join post_cap
