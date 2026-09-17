"""Pull the English Indices of Deprivation 2019, File 7 (all domain ranks,
scores, deciles, and population denominators) from gov.uk.

Run: python ingestion/imd_ingest.py
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import requests

sys.path.append(str(Path(__file__).resolve().parent))
from common.storage import land_raw_file

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("imd_ingest")

IMD_FILE7_URL = (
    "https://assets.publishing.service.gov.uk/media/"
    "5dc407b440f0b6379a7acc8d/"
    "File_7_-_All_IoD2019_Scores__Ranks__Deciles_and_Population_Denominators_3.csv"
)


def main() -> None:
    log.info("Requesting IMD 2019 File 7 from %s", IMD_FILE7_URL)
    resp = requests.get(IMD_FILE7_URL, timeout=90, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    content = resp.content
    log.info("Downloaded %d bytes, content-type=%s", len(content), resp.headers.get("Content-Type"))

    location = land_raw_file(
        source_name="imd2019",
        filename="imd2019_file7_all_scores_ranks_deciles.csv",
        content=content,
    )
    log.info("Landed IMD 2019 File 7 at %s", location)


if __name__ == "__main__":
    main()
