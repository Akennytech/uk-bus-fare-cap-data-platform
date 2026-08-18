"""Load the cleaned NaPTAN Silver-layer CSV from MinIO into Postgres."""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import psycopg2

sys.path.append(str(Path(__file__).resolve().parents[1] / "ingestion"))
from common.storage import get_client  # noqa: E402
from common.config import settings  # noqa: E402

DDL = """
CREATE SCHEMA IF NOT EXISTS silver;
CREATE TABLE IF NOT EXISTS silver.naptan_stops (
  atco_code varchar(20) PRIMARY KEY,
  stop_name text,
  locality_name text,
  admin_area_code varchar(20),
  latitude double precision,
  longitude double precision
);
TRUNCATE TABLE silver.naptan_stops;
"""


def main():
    client = get_client()
    object_name = "naptan/stops/naptan_stops_clean.csv"

    with tempfile.TemporaryDirectory() as tmp:
        local_csv = os.path.join(tmp, "naptan_stops_clean.csv")
        client.fget_object(settings.bucket_silver, object_name, local_csv)

        conn = psycopg2.connect(
            host=settings.postgres_host,
            port=int(settings.postgres_port),
            dbname=settings.postgres_db,
            user=settings.postgres_user,
            password=settings.postgres_password,
        )
        with conn:
            with conn.cursor() as cur:
                cur.execute(DDL)
                with open(local_csv, "r", encoding="utf-8") as f:
                    cur.copy_expert("COPY silver.naptan_stops FROM STDIN WITH CSV HEADER", f)
        conn.close()
        print("Loaded silver.naptan_stops into Postgres.")


if __name__ == "__main__":
    main()
