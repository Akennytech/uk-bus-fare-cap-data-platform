"""Load cleaned IMD 2019 district summary CSV from Silver (MinIO) into
Postgres silver.imd_la_summary.

Run: python warehouse/load_imd_silver.py
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
log = logging.getLogger("load_imd_silver")

DDL = """
CREATE SCHEMA IF NOT EXISTS silver;

CREATE TABLE IF NOT EXISTS silver.imd_la_summary (
    la_code                  TEXT,
    la_name                  TEXT,
    num_lsoas                INTEGER,
    avg_imd_score             NUMERIC,
    avg_imd_rank               NUMERIC,
    avg_imd_decile             NUMERIC,
    avg_income_decile          NUMERIC,
    avg_employment_decile      NUMERIC,
    total_population_mid2015 BIGINT
);
"""


def main() -> None:
    client = get_client()
    object_name = "imd2019/imd_la_summary_clean.csv"
    local_path = str(Path(tempfile.gettempdir()) / "imd_la_summary_clean_download.csv")
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
                cur.execute("TRUNCATE silver.imd_la_summary;")
                with open(local_path, "r", encoding="utf-8") as f:
                    cur.copy_expert(
                        "COPY silver.imd_la_summary FROM STDIN WITH CSV HEADER",
                        f,
                    )
                cur.execute(
                    "SELECT la_name, round(avg_imd_score, 1), round(avg_imd_decile, 1) "
                    "FROM silver.imd_la_summary ORDER BY avg_imd_score DESC LIMIT 5;"
                )
                top5 = cur.fetchall()
                cur.execute("SELECT count(*) FROM silver.imd_la_summary;")
                (count,) = cur.fetchone()
        log.info("Most deprived (by avg IMD score) in the region:")
        for name, score, decile in top5:
            log.info("  %-25s avg score %s, avg decile %s", name, score, decile)
        log.info("Loaded %d rows into silver.imd_la_summary", count)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
