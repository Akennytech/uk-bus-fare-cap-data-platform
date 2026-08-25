"""Load cleaned weather CSV from Silver (MinIO) into Postgres silver.weather_daily.

Run: python warehouse/load_weather_silver.py
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
log = logging.getLogger("load_weather_silver")

DDL = """
CREATE SCHEMA IF NOT EXISTS silver;

CREATE TABLE IF NOT EXISTS silver.weather_daily (
    city              TEXT,
    date              DATE,
    temp_max_c        NUMERIC,
    temp_min_c        NUMERIC,
    precipitation_mm  NUMERIC,
    windspeed_max_kmh NUMERIC
);
"""


def main() -> None:
    client = get_client()
    object_name = "weather/daily/weather_daily_clean.csv"
    local_path = str(Path(tempfile.gettempdir()) / "weather_daily_clean_download.csv")
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
                cur.execute("TRUNCATE silver.weather_daily;")
                with open(local_path, "r", encoding="utf-8") as f:
                    cur.copy_expert(
                        "COPY silver.weather_daily FROM STDIN WITH CSV HEADER",
                        f,
                    )
                cur.execute("SELECT count(*) FROM silver.weather_daily;")
                (count,) = cur.fetchone()
        log.info("Loaded %d rows into silver.weather_daily", count)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
