"""Pull ONS mid-year population estimates by local authority (England & Wales).

Run: python ingestion/ons_ingest.py
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import requests

sys.path.append(str(Path(__file__).resolve().parent))
from common.storage import land_raw_file  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("ons_ingest")

ONS_MYE_URL = (
    "https://www.ons.gov.uk/file?uri=/peoplepopulationandcommunity/"
    "populationandmigration/populationestimates/datasets/"
    "populationestimatesforukenglandandwalesscotlandandnorthernireland/"
    "mid2024/mye24tablesuk.xlsx"
)


def main() -> None:
    log.info("Requesting ONS mid-year population estimates from %s", ONS_MYE_URL)
    resp = requests.get(ONS_MYE_URL, timeout=60, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    content = resp.content

    is_xlsx = content[:2] == b"PK"  # xlsx files are zip archives
    log.info(
        "Downloaded %d bytes, content-type=%s, looks like xlsx: %s",
        len(content), resp.headers.get("Content-Type"), is_xlsx,
    )
    if not is_xlsx:
        log.warning("Response does not look like a valid xlsx file -- first 200 bytes: %r", content[:200])

    location = land_raw_file(
        source_name="ons_population",
        filename="mye_population_estimates.xlsx",
        content=content,
    )
    log.info("Landed ONS population estimates at %s", location)


if __name__ == "__main__":
    main()
