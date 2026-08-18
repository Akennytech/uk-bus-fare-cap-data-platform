-- Staging model: thin, typed pass-through over the Silver-layer NaPTAN
-- Parquet output (loaded into a `raw` schema/table by your loader of choice —
-- e.g. a small PySpark or pandas job that writes silver Parquet into Postgres,
-- or dbt's external tables if you introduce DuckDB/Spark as the query engine).
--
-- This is intentionally a starter stub: fill in the `source()` reference once
-- your loader lands silver.naptan_stops into Postgres.

with source as (

    select * from {{ source('silver', 'naptan_stops') }}

),

renamed as (

    select
        atco_code,
        stop_name,
        locality_name,
        admin_area_code,
        latitude,
        longitude
    from source
    where atco_code is not null

)

select * from renamed
