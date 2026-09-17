"""Bronze -> Silver: clean and validate the NaPTAN bus stop extract with PySpark.

Reads the CSV by column NAME (not a rigid positional schema, since NaPTAN's
real export has 40+ columns) and writes the cleaned result via pandas rather
than Spark's own Hadoop-backed writer, to avoid needing a native winutils.exe
binary on Windows.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "ingestion"))
from common.config import settings
from common.storage import get_client
from pyspark.sql import SparkSession
from pyspark.sql import functions as F


def find_latest_bronze_object(client, bucket, prefix="naptan/"):
    objects = list(client.list_objects(bucket, prefix=prefix, recursive=True))
    if not objects:
        raise RuntimeError(f"No objects found under {bucket}/{prefix} -- run ingestion/naptan_ingest.py first.")
    latest = max(objects, key=lambda o: o.last_modified)
    return latest.object_name


def clean_naptan(spark, local_csv_path):
    raw = (
        spark.read
        .option("header", True)
        .option("multiLine", True)
        .option("escape", '"')
        .csv(local_csv_path)
    )
    print("Actual columns found in file:", raw.columns)

    cleaned = (
        raw
        .filter(F.col("ATCOCode").isNotNull())
        .filter(F.col("Status") == "active")
        .dropDuplicates(["ATCOCode"])
        .withColumn("latitude", F.col("Latitude").cast("double"))
        .withColumn("longitude", F.col("Longitude").cast("double"))
        .filter(F.col("latitude").between(49.5, 61.0))
        .filter(F.col("longitude").between(-8.5, 2.0))
        .select(
            F.col("ATCOCode").alias("atco_code"),
            F.col("CommonName").alias("stop_name"),
            F.col("LocalityName").alias("locality_name"),
            F.col("AdministrativeAreaCode").alias("admin_area_code"),
            "latitude",
            "longitude",
        )
    )

    n_raw, n_clean = raw.count(), cleaned.count()
    dropped = n_raw - n_clean
    print(f"NaPTAN: read {n_raw} rows, kept {n_clean}, dropped {dropped} ({dropped/n_raw:.1%})")
    return cleaned


if __name__ == "__main__":
    client = get_client()
    object_name = find_latest_bronze_object(client, settings.bucket_bronze)
    print(f"Downloading {object_name} from bronze bucket...")

    with tempfile.TemporaryDirectory() as tmp:
        local_csv = os.path.join(tmp, "naptan_stops.csv")
        client.fget_object(settings.bucket_bronze, object_name, local_csv)

        spark = SparkSession.builder.appName("clean_naptan").master("local[*]").getOrCreate()
        spark.sparkContext.setLogLevel("WARN")

        cleaned = clean_naptan(spark, local_csv)

        pdf = cleaned.toPandas()
        local_out = os.path.join(tmp, "naptan_stops_clean.csv")
        pdf.to_csv(local_out, index=False)

        dest = "naptan/stops/naptan_stops_clean.csv"
        client.fput_object(settings.bucket_silver, dest, local_out)
        print(f"Uploaded {len(pdf)} cleaned rows to s3://{settings.bucket_silver}/{dest}")

        spark.stop()
