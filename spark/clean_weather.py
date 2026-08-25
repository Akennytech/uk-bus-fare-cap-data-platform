"""Clean/reshape Open-Meteo daily weather JSON from Bronze into a tidy Silver CSV.

Plain Python (not PySpark) - same reasoning as clean_bods.py: this data
volume doesn't benefit from distributed processing.

Run: python spark/clean_weather.py
"""
from __future__ import annotations

import json
import logging
import sys
import tempfile
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[1] / "ingestion"))
from common.config import settings  # noqa: E402
from common.storage import get_client  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("clean_weather")


def find_latest_weather_objects(client) -> list:
    prefix = "weather/"
    objects = list(client.list_objects(settings.bucket_bronze, prefix=prefix, recursive=True))
    if not objects:
        raise SystemExit(f"No objects found under {prefix} in bucket {settings.bucket_bronze}")
    dts = sorted({o.object_name.split("/")[1] for o in objects if "/" in o.object_name})
    latest_dt = dts[-1]
    latest = [o for o in objects if f"/{latest_dt}/" in o.object_name]
    log.info("Using partition %s: %d files", latest_dt, len(latest))
    return latest


def parse_weather_json(data: dict, city: str) -> list[dict]:
    daily = data.get("daily", {})
    dates = daily.get("time", [])
    tmax = daily.get("temperature_2m_max", [])
    tmin = daily.get("temperature_2m_min", [])
    precip = daily.get("precipitation_sum", [])
    wind = daily.get("windspeed_10m_max", [])

    rows = []
    for i, d in enumerate(dates):
        rows.append(
            {
                "city": city,
                "date": d,
                "temp_max_c": tmax[i] if i < len(tmax) else None,
                "temp_min_c": tmin[i] if i < len(tmin) else None,
                "precipitation_mm": precip[i] if i < len(precip) else None,
                "windspeed_max_kmh": wind[i] if i < len(wind) else None,
            }
        )
    return rows


def main() -> None:
    client = get_client()
    objects = find_latest_weather_objects(client)

    all_rows: list[dict] = []
    for obj in objects:
        filename = obj.object_name.rsplit("/", 1)[-1]
        city = filename.replace("_weather.json", "").capitalize()

        resp = client.get_object(settings.bucket_bronze, obj.object_name)
        content = resp.read()
        resp.close()
        resp.release_conn()

        data = json.loads(content)
        rows = parse_weather_json(data, city)
        all_rows.extend(rows)
        log.info("Parsed %s: %d daily records", city, len(rows))

    df = pd.DataFrame(all_rows)
    before = len(df)
    df = df.dropna(subset=["date", "temp_max_c", "temp_min_c"])
    after = len(df)
    log.info(
        "Weather: extracted %d rows across %d cities, kept %d after dropping incomplete days (%d dropped)",
        before, df["city"].nunique() if not df.empty else 0, after, before - after,
    )

    local_out = str(Path(tempfile.gettempdir()) / "weather_daily_clean.csv")
    df.to_csv(local_out, index=False)

    object_name = "weather/daily/weather_daily_clean.csv"
    client.fput_object(settings.bucket_silver, object_name, local_out)
    log.info("Uploaded %d cleaned rows to s3://%s/%s", after, settings.bucket_silver, object_name)


if __name__ == "__main__":
    main()
