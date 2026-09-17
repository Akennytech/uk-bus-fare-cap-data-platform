"""Clean DfT weekly road fuel prices (Bronze) into a tidy Silver CSV.

Run: python spark/clean_fuel.py
"""
from __future__ import annotations

import logging
import sys
import tempfile
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[1] / "ingestion"))
from common.config import settings
from common.storage import get_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("clean_fuel")

RENAME = {
    "Date": "week_start_date",
    "ULSP (Ultra low sulphur unleaded petrol) Pump price in pence/litre": "petrol_pump_price_ppl",
    "ULSD (Ultra low sulphur diesel) Pump price in pence/litre": "diesel_pump_price_ppl",
    "ULSP (Ultra low sulphur unleaded petrol) Duty rate in pence/litre": "petrol_duty_rate_ppl",
    "ULSD (Ultra low sulphur diesel) Duty rate in pence/litre": "diesel_duty_rate_ppl",
    "ULSP (Ultra low sulphur unleaded petrol) VAT percentage rate": "petrol_vat_pct",
    "ULSD (Ultra low sulphur diesel) VAT percentage rate": "diesel_vat_pct",
}


def find_latest_fuel_object(client):
    prefix = "fuel_prices/"
    objects = list(client.list_objects(settings.bucket_bronze, prefix=prefix, recursive=True))
    if not objects:
        raise SystemExit(f"No objects found under {prefix}")
    return max(objects, key=lambda o: o.object_name)


def main() -> None:
    client = get_client()
    obj = find_latest_fuel_object(client)
    log.info("Using %s", obj.object_name)

    local_path = str(Path(tempfile.gettempdir()) / "fuel_clean_source.csv")
    client.fget_object(settings.bucket_bronze, obj.object_name, local_path)

    df = pd.read_csv(local_path)
    before = len(df)
    df = df.rename(columns=RENAME)
    df["week_start_date"] = pd.to_datetime(df["week_start_date"], format="%d/%m/%Y").dt.date

    df = df.dropna(subset=["week_start_date", "petrol_pump_price_ppl", "diesel_pump_price_ppl"])
    after = len(df)
    log.info("Fuel prices: %d weekly records, kept %d after dropping incomplete rows (%d dropped)",
              before, after, before - after)

    local_out = str(Path(tempfile.gettempdir()) / "fuel_prices_clean.csv")
    df.to_csv(local_out, index=False)

    object_name = "fuel_prices/fuel_prices_clean.csv"
    client.fput_object(settings.bucket_silver, object_name, local_out)
    log.info("Uploaded %d cleaned rows to s3://%s/%s", after, settings.bucket_silver, object_name)


if __name__ == "__main__":
    main()
