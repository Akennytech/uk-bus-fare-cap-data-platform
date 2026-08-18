"""Download the national NaPTAN bus stop dataset and land it in the Bronze layer.

NaPTAN is free, requires no API key, and gives every bus stop in Great Britain
with its location and local authority — this is the DIM_Location / stop
reference data every other dataset joins against, so it's the natural first
ingestion script to get working end to end.

Run: python ingestion/naptan_ingest.py
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import requests

sys.path.append(str(Path(__file__).resolve().parent))
from common.storage import land_raw_file  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("naptan_ingest")

# CSV export of the full NaPTAN dataset (national). Confirm the current
# download endpoint at https://naptan.dft.gov.uk/ before scheduling this in
# production — DfT occasionally moves the export URL between the naptan.dft.gov.uk
# and beta-naptan.dft.gov.uk hosts.
NAPTAN_CSV_URL = "https://naptan.dft.gov.uk/Naptan.ashx?format=csv"


def fetch_naptan(url: str = NAPTAN_CSV_URL, timeout: int = 120) -> bytes:
    log.info("Requesting NaPTAN export from %s", url)
    resp = requests.get(url, timeout=timeout)
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
