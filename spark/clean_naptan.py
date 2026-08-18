"""Bronze -> Silver: clean and validate the NaPTAN bus stop extract with PySpark.

Demonstrates the pattern used for every Bronze->Silver job in this platform:
schema enforcement, null/duplicate handling, and writing partitioned,
columnar Parquet to the Silver layer.

Run locally (adjust the MinIO endpoint/credentials via env vars or spark-defaults):
    spark-submit spark/clean_naptan.py
"""
from __future__ import annotations

from pyspark.sql import SparkSession, functions as F, types as T

NAPTAN_SCHEMA = T.StructType([
    T.StructField("ATCOCode", T.StringType(), False),
    T.StructField("CommonName", T.StringType(), True),
    T.StructField("Easting", T.DoubleType(), True),
    T.StructField("Northing", T.DoubleType(), True),
    T.StructField("Longitude", T.DoubleType(), True),
    T.StructField("Latitude", T.DoubleType(), True),
    T.StructField("LocalityName", T.StringType(), True),
    T.StructField("AdministrativeAreaCode", T.StringType(), True),
    T.StructField("Status", T.StringType(), True),
])


def build_spark(app_name: str = "clean_naptan") -> SparkSession:
    return (
        SparkSession.builder.appName(app_name)
        .config("spark.hadoop.fs.s3a.endpoint", "http://localhost:9000")
        .config("spark.hadoop.fs.s3a.access.key", "minioadmin")
        .config("spark.hadoop.fs.s3a.secret.key", "change_me_locally")
        .config("spark.hadoop.fs.s3a.path.style.access", "true")
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
        .getOrCreate()
    )


def clean_naptan(spark: SparkSession, bronze_path: str, silver_path: str) -> None:
    raw = (
        spark.read.option("header", True)
        .schema(NAPTAN_SCHEMA)
        .csv(bronze_path)
    )

    cleaned = (
        raw
        .filter(F.col("ATCOCode").isNotNull())
        .filter(F.col("Status") == "active")
        .dropDuplicates(["ATCOCode"])
        .withColumn("Latitude", F.col("Latitude").cast("double"))
        .withColumn("Longitude", F.col("Longitude").cast("double"))
        .filter(F.col("Latitude").between(49.5, 61.0))   # sanity bounds for GB
        .filter(F.col("Longitude").between(-8.5, 2.0))
        .withColumnRenamed("ATCOCode", "atco_code")
        .withColumnRenamed("CommonName", "stop_name")
        .withColumnRenamed("LocalityName", "locality_name")
        .withColumnRenamed("AdministrativeAreaCode", "admin_area_code")
        .withColumnRenamed("Latitude", "latitude")
        .withColumnRenamed("Longitude", "longitude")
        .select("atco_code", "stop_name", "locality_name", "admin_area_code", "latitude", "longitude")
    )

    row_count_raw = raw.count()
    row_count_clean = cleaned.count()
    dropped = row_count_raw - row_count_clean
    print(f"NaPTAN: read {row_count_raw} rows, kept {row_count_clean}, dropped {dropped} "
          f"({dropped / row_count_raw:.1%} filtered as inactive/invalid/duplicate)")

    cleaned.write.mode("overwrite").parquet(silver_path)


if __name__ == "__main__":
    spark = build_spark()
    clean_naptan(
        spark,
        bronze_path="s3a://bronze/naptan/dt=*/naptan_stops.csv",
        silver_path="s3a://silver/naptan/stops/",
    )
    spark.stop()
