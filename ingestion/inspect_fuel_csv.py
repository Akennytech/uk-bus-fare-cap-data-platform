import sys
import tempfile
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent))
from common.config import settings  # noqa: E402
from common.storage import get_client  # noqa: E402

client = get_client()
prefix = "fuel_prices/"
objects = list(client.list_objects(settings.bucket_bronze, prefix=prefix, recursive=True))
latest = sorted(objects, key=lambda o: o.object_name)[-1]
print(f"Reading {latest.object_name}")

local_path = str(Path(tempfile.gettempdir()) / "fuel_inspect.csv")
client.fget_object(settings.bucket_bronze, latest.object_name, local_path)

df = pd.read_csv(local_path)
print("Columns:", list(df.columns))
print("\nShape:", df.shape)
print("\nFirst 5 rows:")
print(df.head())
print("\nLast 5 rows:")
print(df.tail())
