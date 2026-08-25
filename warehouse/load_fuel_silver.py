"""Load cleaned weekly fuel prices CSV from Silver (MinIO) into Postgres
silver.fuel_prices_weekly.

Run: python warehouse/load_fuel_silver.py
"""
from __future__ import annotations

import logging
import sys
import tempfile
from pathlib import Path

import psycopg2

sys.path.append(str(Path(__file__).resolve().parents[1] / "ingestion"))
from common.config import settings  # noqa: E402
from common.storage import get_client  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("load_fuel_silver")

DDL = """
CREATE SCHEMA IF NOT EXISTS silver;

CREATE TABLE IF NOT EXISTS silver.fuel_prices_weekly (
    week_start_date       DATE,
    petrol_pump_price_ppl NUMERIC,
    diesel_pump_price_ppl NUMERIC,
    petrol_duty_rate_ppl  NUMERIC,
    diesel_duty_rate_ppl  NUMERIC,
    petrol_vat_pct        NUMERIC,
    diesel_vat_pct        NUMERIC
);
"""


def main() -> None:
    client = get_client()
    object_name = "fuel_prices/fuel_prices_clean.csv"
    local_path = str(Path(tempfile.gettempdir()) / "fuel_prices_clean_download.csv")
    client.fget_object(settings.bucket_silver, object_name, local_path)
    log.info("Downloaded %s to %s", object_name, local_path)

    conn = psycopg2.connect(
        host=settings.postgres_host,
        port=settings.postgres_port,
        dbname=settings.postgres_db,
        user=settings.postgres_user,
        password=settings.postgres_password,
    )
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(DDL)
                cur.execute("TRUNCATE silver.fuel_prices_weekly;")
                with open(local_path, "r", encoding="utf-8") as f:
                    cur.copy_expert(
                        "COPY silver.fuel_prices_weekly FROM STDIN WITH CSV HEADER",
                        f,
                    )
                cur.execute(
                    "SELECT week_start_date, petrol_pump_price_ppl, diesel_pump_price_ppl "
                    "FROM silver.fuel_prices_weekly ORDER BY week_start_date DESC LIMIT 3;"
                )
                latest = cur.fetchall()
                cur.execute("SELECT count(*) FROM silver.fuel_prices_weekly;")
                (count,) = cur.fetchone()
        log.info("Most recent weeks:")
        for wk, petrol, diesel in latest:
            log.info("  %s  petrol %sp/L  diesel %sp/L", wk, petrol, diesel)
        log.info("Loaded %d rows into silver.fuel_prices_weekly", count)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
