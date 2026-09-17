"""Pull DfT weekly road fuel prices (petrol/diesel), by finding the current
CSV link on the gov.uk statistics page rather than hardcoding a filename --
this dataset gets a new file (with a new hash in the URL) published every
week, so a hardcoded link would go stale within days.

Run: python ingestion/fuel_ingest.py
"""
from __future__ import annotations

import logging
import re
import sys
from pathlib import Path

import requests

sys.path.append(str(Path(__file__).resolve().parent))
from common.storage import land_raw_file

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("fuel_ingest")

STATS_PAGE_URL = "https://www.gov.uk/government/statistics/weekly-road-fuel-prices"
CSV_LINK_PATTERN = re.compile(
    r'href="(https://assets\.publishing\.service\.gov\.uk/media/[^"]+\.csv)"'
)


def find_current_csv_url(timeout: int = 30) -> str:
    resp = requests.get(STATS_PAGE_URL, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    matches = CSV_LINK_PATTERN.findall(resp.text)
    if not matches:
        raise RuntimeError(f"No CSV link found on {STATS_PAGE_URL} -- page structure may have changed.")
    log.info("Found %d CSV link(s) on stats page, using the first: %s", len(matches), matches[0])
    return matches[0]


def main() -> None:
    csv_url = find_current_csv_url()
    log.info("Requesting weekly road fuel prices from %s", csv_url)
    resp = requests.get(csv_url, timeout=60, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    content = resp.content
    log.info("Downloaded %d bytes, content-type=%s", len(content), resp.headers.get("Content-Type"))

    location = land_raw_file(
        source_name="fuel_prices",
        filename="weekly_road_fuel_prices.csv",
        content=content,
    )
    log.info("Landed weekly road fuel prices at %s", location)


if __name__ == "__main__":
    main()
