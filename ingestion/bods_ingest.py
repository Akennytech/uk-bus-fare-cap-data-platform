"""Pull bus timetable/route data from the DfT Bus Open Data Service (BODS).

BODS requires a free API key (register at https://www.bus-data.dft.gov.uk/).
This script fetches the dataset catalogue for a given region/operator as a
starting point — extend it to download individual TransXChange/GTFS
timetable files once you've decided which operators/regions to scope into
the platform (recommend starting with 2-3 regions rather than all of GB).

Run: python ingestion/bods_ingest.py
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import requests

sys.path.append(str(Path(__file__).resolve().parent))
from common.config import settings  # noqa: E402
from common.storage import land_raw_file  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("bods_ingest")

BODS_DATASET_API = "https://data.bus-data.dft.gov.uk/api/v1/dataset/"


def fetch_dataset_catalogue(api_key: str, params: dict | None = None, timeout: int = 60) -> bytes:
    if not api_key:
        raise RuntimeError(
            "BODS_API_KEY is not set. Register for a free key at "
            "https://www.bus-data.dft.gov.uk/ and add it to your .env file."
        )
    query = {"api_key": api_key, **(params or {})}
    log.info("Requesting BODS dataset catalogue")
    resp = requests.get(BODS_DATASET_API, params=query, timeout=timeout)
    resp.raise_for_status()
    return resp.content


def main() -> None:
    # TODO: once you've picked target regions/operators, filter the catalogue
    # (e.g. params={"noc": "OPERATOR_CODE"}) and loop over results to download
    # each dataset's TransXChange/GTFS file, landing each one individually.
    content = fetch_dataset_catalogue(settings.bods_api_key)
    location = land_raw_file(
        source_name="bods",
        filename="dataset_catalogue.json",
        content=content,
    )
    log.info("Landed BODS catalogue at %s", location)


if __name__ == "__main__":
    main()
