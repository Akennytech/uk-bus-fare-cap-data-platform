"""Pull BODS timetable datasets for a scoped set of English regions.

Strategy: this project focuses on the East Midlands (Derby, Derbyshire,
Leicester, Leicestershire, Nottingham, Nottinghamshire) rather than
downloading all ~940 published GB timetable datasets - this matches where
NaPTAN's Phase 1 data already showed Leicester as the top-stop-count
locality (482 stops), so the fare-cap-impact story stays regionally
coherent end to end. Extend TARGET_ADMIN_AREAS to widen scope later.

Run: python ingestion/bods_ingest.py
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import requests

sys.path.append(str(Path(__file__).resolve().parent))
from common.config import settings
from common.storage import land_raw_file

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("bods_ingest")

BODS_DATASET_API = "https://data.bus-data.dft.gov.uk/api/v1/dataset/"

# East Midlands admin areas (ATCO codes) - Derby, Derbyshire, Leicester,
# Leicestershire, Nottingham, Nottinghamshire
TARGET_ADMIN_AREAS = {"109", "100", "269", "260", "339", "330"}


def fetch_all_datasets(api_key: str, timeout: int = 60) -> list[dict]:
    if not api_key:
        raise RuntimeError(
            "BODS_API_KEY is not set. Register for a free key at "
            "https://www.bus-data.dft.gov.uk/ and add it to your .env file."
        )
    results: list[dict] = []
    url = BODS_DATASET_API
    params = {"api_key": api_key, "limit": 100}
    page = 1
    while url:
        log.info("Requesting BODS dataset catalogue page %d", page)
        resp = requests.get(url, params=params, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        results.extend(data.get("results", []))
        url = data.get("next")
        params = None  # 'next' URL already carries api_key + offset
        page += 1
    log.info("Fetched %d total published datasets", len(results))
    return results


def filter_target_datasets(datasets: list[dict]) -> list[dict]:
    matched = []
    for ds in datasets:
        if ds.get("status") != "published":
            continue
        admin_codes = {a.get("atco_code") for a in ds.get("adminAreas", [])}
        if admin_codes & TARGET_ADMIN_AREAS:
            matched.append(ds)
    log.info("%d of %d datasets match target admin areas", len(matched), len(datasets))
    return matched


def download_dataset_zip(ds: dict, api_key: str, timeout: int = 120) -> bytes:
    resp = requests.get(ds["url"], params={"api_key": api_key}, timeout=timeout)
    resp.raise_for_status()
    return resp.content


def main() -> None:
    api_key = settings.bods_api_key
    all_datasets = fetch_all_datasets(api_key)

    catalogue_location = land_raw_file(
        source_name="bods",
        filename="dataset_catalogue_full.json",
        content=json.dumps(all_datasets).encode("utf-8"),
    )
    log.info(
        "Landed full BODS catalogue (%d datasets) at %s",
        len(all_datasets),
        catalogue_location,
    )

    targets = filter_target_datasets(all_datasets)

    landed = []
    for ds in targets:
        try:
            content = download_dataset_zip(ds, api_key)
        except requests.exceptions.RequestException as exc:
            log.warning(
                "Failed to download dataset %s (%s): %s",
                ds.get("id"),
                ds.get("operatorName"),
                exc,
            )
            continue
        safe_operator = (ds.get("operatorName") or "unknown").replace(" ", "_")
        filename = f"{ds['id']}_{safe_operator}.zip"
        location = land_raw_file(
            source_name="bods_timetables", filename=filename, content=content
        )
        landed.append(location)
        log.info(
            "Landed %s (%d bytes) at %s", ds.get("operatorName"), len(content), location
        )

    log.info("Done. Landed %d/%d target timetable datasets.", len(landed), len(targets))


if __name__ == "__main__":
    main()
