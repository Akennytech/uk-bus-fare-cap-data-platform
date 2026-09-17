"""Pull historical daily weather from Open-Meteo for the project's core
East Midlands cities (Derby, Leicester, Nottingham) - free, no API key
required. Covers roughly the last 2.5 years, giving enough history for a
meaningful dim_weather dimension.

Run: python ingestion/weather_ingest.py
"""
from __future__ import annotations

import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

sys.path.append(str(Path(__file__).resolve().parent))
from common.storage import land_raw_file

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("weather_ingest")

OPEN_METEO_ARCHIVE_API = "https://archive-api.open-meteo.com/v1/archive"

LOCATIONS = {
    "Derby": (52.9225, -1.4746),
    "Leicester": (52.6369, -1.1398),
    "Nottingham": (52.9548, -1.1581),
}

DAILY_VARS = "temperature_2m_max,temperature_2m_min,precipitation_sum,windspeed_10m_max"


def fetch_weather(lat: float, lon: float, start_date: str, end_date: str, timeout: int = 60) -> bytes:
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "daily": DAILY_VARS,
        "timezone": "Europe/London",
    }
    resp = requests.get(OPEN_METEO_ARCHIVE_API, params=params, timeout=timeout)
    resp.raise_for_status()
    return resp.content


def main() -> None:
    end_date = datetime.now(tz=timezone.utc).date() - timedelta(days=1)  # archive API needs a fully-completed day
    start_date = end_date - timedelta(days=int(365 * 2.5))

    log.info("Fetching weather from %s to %s for %d locations", start_date, end_date, len(LOCATIONS))

    for city, (lat, lon) in LOCATIONS.items():
        try:
            content = fetch_weather(lat, lon, start_date.isoformat(), end_date.isoformat())
        except requests.exceptions.RequestException as exc:
            log.warning("Failed to fetch weather for %s: %s", city, exc)
            continue

        location = land_raw_file(
            source_name="weather",
            filename=f"{city.lower()}_weather.json",
            content=content,
        )
        log.info("Landed %s weather (%d bytes) at %s", city, len(content), location)


if __name__ == "__main__":
    main()
