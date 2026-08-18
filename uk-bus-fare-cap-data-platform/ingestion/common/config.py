"""Shared configuration for all ingestion scripts.

Loads settings from a .env file (see .env.example) so no secrets are hard-coded.
"""
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    bods_api_key: str = os.getenv("BODS_API_KEY", "")

    minio_endpoint: str = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    minio_root_user: str = os.getenv("MINIO_ROOT_USER", "minioadmin")
    minio_root_password: str = os.getenv("MINIO_ROOT_PASSWORD", "change_me_locally")
    bucket_bronze: str = os.getenv("MINIO_BUCKET_BRONZE", "bronze")
    bucket_silver: str = os.getenv("MINIO_BUCKET_SILVER", "silver")

    postgres_host: str = os.getenv("POSTGRES_HOST", "localhost")
    postgres_port: str = os.getenv("POSTGRES_PORT", "5432")
    postgres_db: str = os.getenv("POSTGRES_DB", "bus_fare_cap")
    postgres_user: str = os.getenv("POSTGRES_USER", "postgres")
    postgres_password: str = os.getenv("POSTGRES_PASSWORD", "change_me_locally")


settings = Settings()
