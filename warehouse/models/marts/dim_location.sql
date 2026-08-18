-- Example gold-layer dimension build: conforms NaPTAN stop locality data with
-- ONS population and IMD 2019 deprivation deciles onto a single local authority
-- grain. Extend the joins here once stg_ons_population / stg_imd_2019 exist.

with stops as (

    select
        admin_area_code as la_code,
        locality_name,
        count(*) as stop_count
    from {{ ref('stg_naptan_stops') }}
    group by 1, 2

)

select
    la_code,
    locality_name,
    stop_count
    -- , ons_population
    -- , imd_decile
    -- , urban_rural_class
from stops
