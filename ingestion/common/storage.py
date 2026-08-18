"""Thin wrapper around MinIO (S3-compatible) for landing raw files into the
Bronze layer. Using the S3 API (via boto3 or the minio SDK) here means this
code needs almost no changes if the platform is ever pointed at real AWS S3
or Azure Blob's S3-compatible endpoint later.
"""
from __future__ import annotations

import io
from datetime import date

from minio import Minio
from minio.error import S3Error

from .config import settings


def get_client() -> Minio:
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_root_user,
        secret_key=settings.minio_root_password,
        secure=False,  # local Docker MinIO uses plain HTTP
    )


def ensure_bucket(client: Minio, bucket: str) -> None:
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)


def land_raw_file(source_name: str, filename: str, content: bytes, run_date: date | None = None) -> str:
    """Write a raw file to the Bronze bucket, partitioned by source and date.

    Path convention: {bucket}/{source_name}/dt={YYYY-MM-DD}/{filename}
    This partitioning makes it trivial for PySpark to read a whole day's
    landing zone, and keeps every ingestion run immutable and auditable.
    """
    run_date = run_date or date.today()
    client = get_client()
    ensure_bucket(client, settings.bucket_bronze)

    object_name = f"{source_name}/dt={run_date.isoformat()}/{filename}"
    try:
        client.put_object(
            settings.bucket_bronze,
            object_name,
            data=io.BytesIO(content),
            length=len(content),
        )
    except S3Error as exc:  # pragma: no cover - surfaced to caller/logs
        raise RuntimeError(f"Failed to land {object_name}: {exc}") from exc

    return f"s3://{settings.bucket_bronze}/{object_name}"
