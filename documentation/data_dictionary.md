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
