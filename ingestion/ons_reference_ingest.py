"""Land ONS population estimates and English Indices of Deprivation 2019
reference data into Bronze.

Both are published as direct CSV downloads that are updated periodically —
confirm current URLs before scheduling:
  - ONS population estimates: https://www.ons.gov.uk/peoplepopulationandcommunity/
    populationandmigration/populationestimates
  - IMD 2019: https://www.gov.uk/government/statistics/english-indices-of-deprivation-2019

Run: python ingestion/ons_reference_ingest.py --population-url <csv> --imd-url <csv>
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
log = logging.getLogger("ons_reference_ingest")


def fetch(url: str, timeout: int = 60) -> bytes:
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    return resp.content


def main(population_url: str | None, imd_url: str | None) -> None:
    if population_url:
        content = fetch(population_url)
        loc = land_raw_file("ons_population", "population_estimates.csv", content)
        log.info("Landed population estimates at %s", loc)

    if imd_url:
        content = fetch(imd_url)
        loc = land_raw_file("imd_2019", "indices_of_deprivation_2019.csv", content)
        log.info("Landed IMD 2019 at %s", loc)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--population-url", help="Direct CSV URL for ONS population estimates")
    parser.add_argument("--imd-url", help="Direct CSV URL for English Indices of Deprivation 2019")
    args = parser.parse_args()
    main(args.population_url, args.imd_url)
