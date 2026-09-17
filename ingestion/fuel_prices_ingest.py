"""Land the DfT weekly road fuel prices CSV into Bronze.

DfT publishes this as a downloadable CSV/ODS alongside each weekly statistics
release. Confirm the current file link at
https://www.gov.uk/government/statistics/weekly-road-fuel-prices before
scheduling, since DfT reissues a new document URL with each release.

Run: python ingestion/fuel_prices_ingest.py --url <csv_url>
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import requests

sys.path.append(str(Path(__file__).resolve().parent))
from common.storage import land_raw_file

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("fuel_prices_ingest")


def fetch_fuel_prices(url: str, timeout: int = 60) -> bytes:
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    return resp.content


def main(url: str) -> None:
    content = fetch_fuel_prices(url)
    location = land_raw_file(
        source_name="fuel_prices",
        filename="weekly_road_fuel_prices.csv",
        content=content,
    )
    log.info("Landed fuel prices extract at %s", location)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--url",
        required=True,
        help="Direct CSV/ODS URL for the current weekly road fuel prices release "
        "(find it at gov.uk/government/statistics/weekly-road-fuel-prices)",
    )
    args = parser.parse_args()
    main(args.url)
