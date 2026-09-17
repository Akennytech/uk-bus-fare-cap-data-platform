"""Load cleaned ONS population CSV from Silver (MinIO) into Postgres silver.ons_population.

Run: python warehouse/load_ons_silver.py
"""
from __future__ import annotations

import logging
import sys
import tempfile
from pathlib import Path

import psycopg2

sys.path.append(str(Path(__file__).resolve().parents[1] / "ingestion"))
from common.config import settings
from common.storage import get_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("load_ons_silver")

DDL = """
CREATE SCHEMA IF NOT EXISTS silver;

CREATE TABLE IF NOT EXISTS silver.ons_population (
    la_code             TEXT,
    la_name             TEXT,
    geography_type      TEXT,
    population_mid2024  BIGINT
);
"""


def main() -> None:
    client = get_client()
    object_name = "ons_population/ons_population_clean.csv"
    local_path = str(Path(tempfile.gettempdir()) / "ons_population_clean_download.csv")
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
        with conn, conn.cursor() as cur:
            cur.execute(DDL)
            cur.execute("TRUNCATE silver.ons_population;")
            with open(local_path, "r", encoding="utf-8") as f:
                cur.copy_expert(
                    "COPY silver.ons_population FROM STDIN WITH CSV HEADER",
                    f,
                )
            cur.execute("SELECT la_name, population_mid2024 FROM silver.ons_population ORDER BY population_mid2024 DESC;")
            rows = cur.fetchall()
        for name, pop in rows:
            log.info("  %-16s %s", name, f"{pop:,}")
        log.info("Loaded %d rows into silver.ons_population", len(rows))
    finally:
        conn.close()


if __name__ == "__main__":
    main()
