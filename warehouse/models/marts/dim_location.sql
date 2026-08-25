-- Conformed location dimension at the "ATCO admin area" grain (Derby,
-- Derbyshire, Leicester, Leicestershire, Nottingham, Nottinghamshire) --
-- the grain shared by NaPTAN, BODS and ONS population. IMD 2019 publishes
-- at the lower-tier district level instead (25 districts within these same
-- six areas), so it's re-aggregated up to this grain using a
-- population-weighted average via the imd_district_to_region seed.
--
-- IMPORTANT (see ADR-004 in documentation/data_dictionary.md): NaPTAN's own
-- AdministrativeAreaCode field and BODS's adminAreas.atco_code field are
-- DIFFERENT numbering schemes for the same six areas, despite both being
-- called "ATCO admin area codes". Verified empirically against known
-- suburbs/towns (e.g. Chaddesden/Alvaston -> Derby=017, not BODS's 109;
-- Chesterfield/Ilkeston/Matlock -> Derbyshire=075, not BODS's 100).
-- atco_admin_area_lookup.csv uses NaPTAN's scheme, since this model's
-- stop-count join is against silver.naptan_stops.

with population as (
    select la_code, la_name, geography_type, population_mid2024
    from {{ ref('stg_ons_population') }}
),

stop_counts as (
    select
        lookup.la_name,
        count(*) as stop_count
    from {{ ref('stg_naptan_stops') }} as stops
    inner join {{ ref('atco_admin_area_lookup') }} as lookup
        on stops.admin_area_code::text = lookup.atco_admin_area_code::text
    group by 1
),

imd_weighted as (
    select
        region.region_name as la_name,
        sum(imd.avg_imd_score * imd.total_population_mid2015)
            / nullif(sum(imd.total_population_mid2015), 0) as avg_imd_score,
        sum(imd.avg_imd_decile * imd.total_population_mid2015)
            / nullif(sum(imd.total_population_mid2015), 0) as avg_imd_decile
    from {{ ref('stg_imd_la_summary') }} as imd
    inner join {{ ref('imd_district_to_region') }} as region
        on imd.district_name = region.district_name
    group by 1
)

select
    row_number() over (order by population.la_code) as location_key,
    population.la_code,
    population.la_name,
    population.geography_type,
    'East Midlands' as region,
    population.population_mid2024 as ons_population,
    stop_counts.stop_count,
    round(imd_weighted.avg_imd_score, 1) as avg_imd_score,
    round(imd_weighted.avg_imd_decile, 1) as avg_imd_decile
from population
left join stop_counts on population.la_name = stop_counts.la_name
left join imd_weighted on population.la_name = imd_weighted.la_name
order by population.la_code
