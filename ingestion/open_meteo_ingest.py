"""Pull daily historical weather for a set of local-authority reference points
from the free Open-Meteo API — no API key or signup required.

Run: python ingestion/open_meteo_ingest.py
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import requests

sys.path.append(str(Path(__file__).resolve().parent))
from common.storage import land_raw_file

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("open_meteo_ingest")

OPEN_METEO_URL = "https://archive-api.open-meteo.com/v1/archive"

# A small starter set of reference points (regional hub cities). Expand this
# list (or drive it from DIM_Location once built) to cover every LA you want
# weather-enriched analysis for.
REFERENCE_POINTS = [
    {"name": "Manchester", "lat": 53.4808, "lon": -2.2426},
    {"name": "Leeds", "lat": 53.8008, "lon": -1.5491},
    {"name": "Newcastle", "lat": 54.9783, "lon": -1.6178},
    {"name": "Bristol", "lat": 51.4545, "lon": -2.5879},
    {"name": "Birmingham", "lat": 52.4862, "lon": -1.8904},
]


def fetch_weather(lat: float, lon: float, start_date: str, end_date: str, timeout: int = 60) -> bytes:
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "daily": "temperature_2m_mean,precipitation_sum",
        "timezone": "Europe/London",
    }
    resp = requests.get(OPEN_METEO_URL, params=params, timeout=timeout)
    resp.raise_for_status()
    return resp.content


def main(start_date: str = "2025-01-01", end_date: str = "2025-12-31") -> None:
    for point in REFERENCE_POINTS:
        content = fetch_weather(point["lat"], point["lon"], start_date, end_date)
        location = land_raw_file(
            source_name="open_meteo",
            filename=f"{point['name'].lower()}_{start_date}_{end_date}.json",
            content=content,
        )
        log.info("Landed weather for %s at %s", point["name"], location)


if __name__ == "__main__":
    main()
