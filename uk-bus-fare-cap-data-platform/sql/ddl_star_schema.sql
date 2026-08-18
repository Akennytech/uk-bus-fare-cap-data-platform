-- Gold-layer star schema for the UK £2 Bus Fare Cap platform.
-- Run against the `bus_fare_cap` PostgreSQL database (see docker-compose.yml).
-- This is also mounted into the Postgres container's initdb.d, so it runs
-- automatically the first time the container starts.

CREATE SCHEMA IF NOT EXISTS gold;

-- ==========================================================
-- Dimensions
-- ==========================================================

CREATE TABLE IF NOT EXISTS gold.dim_date (
    date_key        INT PRIMARY KEY,        -- YYYYMMDD
    full_date       DATE NOT NULL,
    year            SMALLINT NOT NULL,
    quarter         SMALLINT NOT NULL,
    month           SMALLINT NOT NULL,
    month_name      VARCHAR(20) NOT NULL,
    day_of_week     VARCHAR(10) NOT NULL,
    day_type        VARCHAR(10) NOT NULL,    -- Weekday / Saturday / Sunday
    is_post_cap_period BOOLEAN NOT NULL      -- TRUE for dates >= 2027-01-01
);

CREATE TABLE IF NOT EXISTS gold.dim_route (
    route_key       SERIAL PRIMARY KEY,
    route_id        VARCHAR(50) NOT NULL,
    route_name      VARCHAR(200),
    operator_key    INT,
    route_type      VARCHAR(50)              -- Urban / Rural / Coastal / Interurban
);

CREATE TABLE IF NOT EXISTS gold.dim_operator (
    operator_key    SERIAL PRIMARY KEY,
    operator_id     VARCHAR(50) NOT NULL,
    operator_name   VARCHAR(200),
    region          VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS gold.dim_location (
    location_key    SERIAL PRIMARY KEY,
    la_code         VARCHAR(20) NOT NULL,    -- ONS local authority code
    la_name         VARCHAR(200),
    region          VARCHAR(100),
    ons_population  INT,
    imd_decile      SMALLINT,                -- 1 = most deprived, 10 = least
    urban_rural_class VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS gold.dim_fare_policy (
    fare_policy_key SERIAL PRIMARY KEY,
    period_name     VARCHAR(50) NOT NULL,    -- 'Pre-cap', '£3 cap', '£2 cap'
    cap_amount      NUMERIC(5,2),
    effective_from  DATE NOT NULL,
    effective_to    DATE
);

CREATE TABLE IF NOT EXISTS gold.dim_weather (
    weather_key     SERIAL PRIMARY KEY,
    observation_date DATE NOT NULL,
    la_code         VARCHAR(20),
    mean_temp_c     NUMERIC(4,1),
    precipitation_mm NUMERIC(6,1),
    condition       VARCHAR(50)
);

-- ==========================================================
-- Facts
-- ==========================================================

CREATE TABLE IF NOT EXISTS gold.fact_bus_service_activity (
    fact_key            BIGSERIAL PRIMARY KEY,
    date_key            INT NOT NULL REFERENCES gold.dim_date(date_key),
    route_key           INT NOT NULL REFERENCES gold.dim_route(route_key),
    operator_key        INT NOT NULL REFERENCES gold.dim_operator(operator_key),
    location_key        INT NOT NULL REFERENCES gold.dim_location(location_key),
    fare_policy_key      INT NOT NULL REFERENCES gold.dim_fare_policy(fare_policy_key),
    weather_key         INT REFERENCES gold.dim_weather(weather_key),
    scheduled_trips     INT NOT NULL DEFAULT 0,
    avg_fare            NUMERIC(6,2),
    est_passenger_index NUMERIC(10,2),        -- documented service-level proxy, see README
    delay_minutes       NUMERIC(6,2)
);

CREATE TABLE IF NOT EXISTS gold.fact_household_savings (
    fact_key            BIGSERIAL PRIMARY KEY,
    date_key            INT NOT NULL REFERENCES gold.dim_date(date_key),
    location_key        INT NOT NULL REFERENCES gold.dim_location(location_key),
    household_type      VARCHAR(50) NOT NULL, -- e.g. 'Single commuter', 'Family'
    weekly_cost_pre_cap  NUMERIC(8,2),
    weekly_cost_post_cap NUMERIC(8,2),
    est_annual_saving    NUMERIC(9,2),
    assumption_notes     TEXT                  -- always populated: journeys/week, fare basis, etc.
);

CREATE INDEX IF NOT EXISTS idx_fact_activity_date ON gold.fact_bus_service_activity(date_key);
CREATE INDEX IF NOT EXISTS idx_fact_activity_route ON gold.fact_bus_service_activity(route_key);
CREATE INDEX IF NOT EXISTS idx_fact_savings_date ON gold.fact_household_savings(date_key);
