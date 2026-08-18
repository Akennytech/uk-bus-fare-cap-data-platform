# Data quality — Great Expectations

This folder is where the Great Expectations project (`great_expectations init`)
lives once initialised. Recommended suites for Week 3 of the roadmap:

## `naptan_silver_suite`

- `expect_column_values_to_not_be_null`: `atco_code`
- `expect_column_values_to_be_unique`: `atco_code`
- `expect_column_values_to_be_between`: `latitude` (49.5–61.0), `longitude` (-8.5–2.0)
- `expect_table_row_count_to_be_between`: sanity bounds based on known NaPTAN size

## `bods_silver_suite`

- Schema conformance against the TransXChange/GTFS field set you extract
- `expect_column_values_to_be_in_set`: route_type in expected categories
- Freshness check: latest ingested date within N days of run date

## `gold_fact_suite` (run via dbt tests, see `warehouse/models/marts/marts.yml`)

- Referential integrity between every fact table and its dimensions
  (dbt `relationships` test)
- `not_null` and `unique` on every surrogate key
- `accepted_values` on `dim_date.is_post_cap_period` (true/false only)

## Wiring into the pipeline

Run `great_expectations checkpoint run <suite_name>` as an Airflow task
immediately after each Silver-layer write, before the dbt run task —
failures should stop the DAG rather than letting bad data reach Gold. See
the "quality gates at every layer" note in the architecture diagram.
