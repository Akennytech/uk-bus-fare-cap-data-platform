# Data dictionary (starter)

Fill this in as each Gold-layer table is built. Keep it in sync with
`sql/ddl_star_schema.sql` and the dbt model docs (`dbt docs generate`).

## gold.fact_bus_service_activity

Grain: one row per route, per stop-pattern, per scheduled service date, per time-band.

| Column | Type | Description | Source |
|---|---|---|---|
| date_key | int | FK to dim_date | derived |
| route_key | int | FK to dim_route | BODS |
| operator_key | int | FK to dim_operator | BODS |
| location_key | int | FK to dim_location | NaPTAN + ONS |
| fare_policy_key | int | FK to dim_fare_policy | GOV.UK policy dates |
| weather_key | int | FK to dim_weather | Open-Meteo |
| scheduled_trips | int | Count of scheduled departures | BODS timetable |
| avg_fare | numeric | Average advertised fare | BODS fares data / DfT stats |
| est_passenger_index | numeric | **Modelled service-level demand proxy** — not a direct passenger count. See README "Data limitations". | derived |
| delay_minutes | numeric | Average delay where punctuality data available | BODS / DfT |

## gold.fact_household_savings

Grain: one row per local authority, per household type, per month.

| Column | Type | Description | Source |
|---|---|---|---|
| weekly_cost_pre_cap | numeric | Modelled weekly cost under the £3 cap | derived, assumptions in `assumption_notes` |
| weekly_cost_post_cap | numeric | Modelled weekly cost under the £2 cap | derived |
| est_annual_saving | numeric | Modelled annual saving | derived |
| assumption_notes | text | Journeys/week and fare basis used — always populated, never blank | — |

## ADR log

Record architecture decisions here as you make them, e.g.:

- **ADR-001**: Chose service-level scheduled-trips as the demand proxy instead
  of attempting to scrape/estimate ticket sales, because no reliable open
  source exists for GB bus patronage at route grain. Revisit if DfT publishes
  finer-grained open patronage data.

- **ADR-004**: NaPTAN's own `AdministrativeAreaCode` field and BODS's
  `adminAreas.atco_code` field are DIFFERENT numbering schemes for the same
  six East Midlands areas, despite both being called "ATCO admin area
  codes." Verified empirically against known suburbs/towns (e.g.
  Chaddesden/Alvaston/Spondon confirm Derby=017 in NaPTAN's scheme, not
  BODS's 109; Chesterfield/Ilkeston/Matlock confirm Derbyshire=075, not
  BODS's 100). `dim_location`'s stop-count join uses NaPTAN's own scheme via
  `seeds/atco_admin_area_lookup.csv`, since it joins against
  `silver.naptan_stops`. Separately, that seed's zero-padded codes (`017`,
  `075`, etc.) were initially silently corrupted by dbt seed's automatic
  column-type inference, which read them as integers and dropped the
  leading zero -- fixed by declaring `column_types: {atco_admin_area_code:
  varchar(10)}` in `seeds/seeds.yml`. Two real lessons: don't assume two
  government datasets share a code scheme just because it looks the same,
  and always pin seed column types for anything that looks numeric but
  isn't (codes, IDs, postcodes).

- **ADR-005**: `fact_bus_service_activity` is built at (route, day-of-week
  pattern) grain, not the original DDL's "per scheduled service date"
  grain. `clean_bods.py` counts `VehicleJourney` elements per (operator,
  line, day-pattern) from TransXChange -- it tells you how much service a
  route runs on e.g. a Monday-to-Friday pattern, not which exact calendar
  dates it ran. Resolving that into a true daily calendar would mean
  expanding each OperatingProfile day-pattern against a real date range,
  which the current ingestion doesn't do. `date_key`, `weather_key`,
  `location_key`, `avg_fare` and `delay_minutes` are dropped from this fact
  as a result -- no source data resolves them at this grain. Revisit if/when
  BODS ingestion is extended to resolve full operating calendars.
- **ADR-006**: `fact_household_savings` is built at (location, household
  type) grain -- a single static GBP3-cap-vs-GBP2-cap comparison -- not the
  original DDL's "per month" grain. Both the household journey-frequency
  assumptions (`seeds/household_travel_assumptions.csv`) and the cap amount
  are flat within a policy period, so a literal per-month grain would just
  repeat identical rows 12x with no analytical value. Every fare-capped
  journey is assumed to hit the cap amount exactly, documented in
  `assumption_notes` on every row.
