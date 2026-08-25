-- Static reference periods, sourced from the fare_policy_periods seed.
-- See seed file / ADR log for sourcing notes and caveats on exact 2023-24
-- extension dates.
select
    row_number() over (order by effective_from) as fare_policy_key,
    period_name,
    cap_amount,
    effective_from,
    effective_to,
    assumption_notes
from {{ ref('fare_policy_periods') }}
