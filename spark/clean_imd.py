"""Aggregate IMD 2019 LSOA-level deprivation data (Bronze) up to local
authority district level for the project's target East Midlands districts,
into a tidy Silver CSV.

Run: python spark/clean_imd.py
"""
from __future__ import annotations

import logging
import sys
import tempfile
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[1] / "ingestion"))
from common.config import settings
from common.storage import get_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("clean_imd")

TARGET_DISTRICTS = {
    "Derby", "Leicester", "Nottingham",
    "Amber Valley", "Bolsover", "Chesterfield", "Derbyshire Dales", "Erewash",
    "High Peak", "North East Derbyshire", "South Derbyshire",
    "Blaby", "Charnwood", "Harborough", "Hinckley and Bosworth", "Melton",
    "North West Leicestershire", "Oadby and Wigston",
    "Ashfield", "Bassetlaw", "Broxtowe", "Gedling", "Mansfield",
    "Newark and Sherwood", "Rushcliffe",
}

COLS_NEEDED = {
    "LSOA code (2011)": "lsoa_code",
    "Local Authority District code (2019)": "la_code",
    "Local Authority District name (2019)": "la_name",
    "Index of Multiple Deprivation (IMD) Score": "imd_score",
    "Index of Multiple Deprivation (IMD) Rank (where 1 is most deprived)": "imd_rank",
    "Index of Multiple Deprivation (IMD) Decile (where 1 is most deprived 10% of LSOAs)": "imd_decile",
    "Income Decile (where 1 is most deprived 10% of LSOAs)": "income_decile",
    "Employment Decile (where 1 is most deprived 10% of LSOAs)": "employment_decile",
    "Total population: mid 2015 (excluding prisoners)": "population_mid2015",
}


def find_latest_imd_object(client):
    prefix = "imd2019/"
    objects = list(client.list_objects(settings.bucket_bronze, prefix=prefix, recursive=True))
    if not objects:
        raise SystemExit(f"No objects found under {prefix}")
    return max(objects, key=lambda o: o.object_name)


def main() -> None:
    client = get_client()
    obj = find_latest_imd_object(client)
    log.info("Using %s", obj.object_name)

    local_path = str(Path(tempfile.gettempdir()) / "imd2019_clean_source.csv")
    client.fget_object(settings.bucket_bronze, obj.object_name, local_path)

    df = pd.read_csv(local_path, usecols=list(COLS_NEEDED.keys()))
    df = df.rename(columns=COLS_NEEDED)

    before = len(df)
    df = df[df["la_name"].isin(TARGET_DISTRICTS)]
    after = len(df)
    log.info("IMD: %d LSOAs nationally, %d LSOAs kept in target districts (%d dropped)", before, after, before - after)

    summary = (
        df.groupby(["la_code", "la_name"])
        .agg(
            num_lsoas=("lsoa_code", "count"),
            avg_imd_score=("imd_score", "mean"),
            avg_imd_rank=("imd_rank", "mean"),
            avg_imd_decile=("imd_decile", "mean"),
            avg_income_decile=("income_decile", "mean"),
            avg_employment_decile=("employment_decile", "mean"),
            total_population_mid2015=("population_mid2015", "sum"),
        )
        .reset_index()
        .sort_values("avg_imd_score", ascending=False)
    )

    log.info("Aggregated to %d local authority districts", len(summary))

    local_out = str(Path(tempfile.gettempdir()) / "imd_la_summary_clean.csv")
    summary.to_csv(local_out, index=False)

    object_name = "imd2019/imd_la_summary_clean.csv"
    client.fput_object(settings.bucket_silver, object_name, local_out)
    log.info("Uploaded %d rows to s3://%s/%s", len(summary), settings.bucket_silver, object_name)


if __name__ == "__main__":
    main()
