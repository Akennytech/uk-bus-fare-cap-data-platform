"""Download the national NaPTAN bus stop dataset and land it in the Bronze layer.

NaPTAN is free and requires no API key. As of 2026 the dataset is served via
DfT's REST API (the old naptan.dft.gov.uk/Naptan.ashx export was retired) --
see https://naptan.api.dft.gov.uk/swagger for the full spec.

Run: python ingestion/naptan_ingest.py
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import requests

sys.path.append(str(Path(__file__).resolve().parent))
from common.storage import land_raw_file

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("naptan_ingest")

NAPTAN_API_URL = "https://naptan.api.dft.gov.uk/v1/access-nodes"


def fetch_naptan(url: str = NAPTAN_API_URL, timeout: int = 180) -> bytes:
    log.info("Requesting NaPTAN export from %s", url)
    resp = requests.get(url, params={"dataFormat": "csv"}, timeout=timeout)
    resp.raise_for_status()
    log.info("Downloaded %d bytes", len(resp.content))
    return resp.content


def main() -> None:
    content = fetch_naptan()
    if not content:
        raise RuntimeError("NaPTAN download returned no content")

    location = land_raw_file(
        source_name="naptan",
        filename="naptan_stops.csv",
        content=content,
    )
    log.info("Landed NaPTAN extract at %s", location)


if __name__ == "__main__":
    main()
