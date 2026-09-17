"""Extract mid-2024 total population for the project's target local
authorities from the ONS MYE2 workbook (Bronze) into a tidy Silver CSV.

Run: python spark/clean_ons.py
"""
from __future__ import annotations

import logging
import sys
import tempfile
from pathlib import Path

import openpyxl
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[1] / "ingestion"))
from common.config import settings
from common.storage import get_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("clean_ons")

TARGET_LA_NAMES = {"Derby", "Derbyshire", "Leicester", "Leicestershire", "Nottingham", "Nottinghamshire"}


def find_latest_ons_object(client):
    prefix = "ons_population/"
    objects = list(client.list_objects(settings.bucket_bronze, prefix=prefix, recursive=True))
    if not objects:
        raise SystemExit(f"No objects found under {prefix}")
    return max(objects, key=lambda o: o.object_name)


def main() -> None:
    client = get_client()
    obj = find_latest_ons_object(client)
    log.info("Using %s", obj.object_name)

    local_path = str(Path(tempfile.gettempdir()) / "ons_mye_clean.xlsx")
    client.fget_object(settings.bucket_bronze, obj.object_name, local_path)

    wb = openpyxl.load_workbook(local_path, read_only=True, data_only=True)
    ws = wb["MYE2 - Persons"]

    rows_iter = ws.iter_rows(values_only=True)
    header = None
    matched = []
    for row in rows_iter:
        if row and row[0] == "Code":
            header = row
            continue
        if header is None:
            continue
        code, name, geography = row[0], row[1], row[2]
        all_ages = row[3]
        if name in TARGET_LA_NAMES:
            matched.append(
                {
                    "la_code": code,
                    "la_name": name,
                    "geography_type": geography,
                    "population_mid2024": all_ages,
                }
            )

    log.info("Matched %d of %d target local authorities: %s",
              len(matched), len(TARGET_LA_NAMES), sorted(r["la_name"] for r in matched))

    missing = TARGET_LA_NAMES - {r["la_name"] for r in matched}
    if missing:
        log.warning("Did not find these target names in the sheet: %s", missing)

    df = pd.DataFrame(matched)
    local_out = str(Path(tempfile.gettempdir()) / "ons_population_clean.csv")
    df.to_csv(local_out, index=False)

    object_name = "ons_population/ons_population_clean.csv"
    client.fput_object(settings.bucket_silver, object_name, local_out)
    log.info("Uploaded %d rows to s3://%s/%s", len(df), settings.bucket_silver, object_name)


if __name__ == "__main__":
    main()
