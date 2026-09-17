"""One-off: pull the IMD 2019 CSV back out of Bronze and print its header
and first few rows, and the distinct Local Authority District names for
our target counties, so we can build the right filter/aggregation.
"""
import sys
import tempfile
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent))
from common.config import settings
from common.storage import get_client

client = get_client()
prefix = "imd2019/"
objects = list(client.list_objects(settings.bucket_bronze, prefix=prefix, recursive=True))
latest = max(objects, key=lambda o: o.object_name)
print(f"Reading {latest.object_name}")

local_path = str(Path(tempfile.gettempdir()) / "imd2019_inspect.csv")
client.fget_object(settings.bucket_bronze, latest.object_name, local_path)

df = pd.read_csv(local_path, nrows=5)
print("Columns:")
for c in df.columns:
    print(" -", c)

print("\nFirst 3 rows (first 6 columns only):")
print(df.iloc[:3, :6])

full = pd.read_csv(local_path, usecols=[c for c in df.columns if "Local Authority District" in c])
la_col = next(c for c in full.columns if "Local Authority District name" in c)
target_districts = {
    "Derby", "Leicester", "Nottingham",
    "Amber Valley", "Bolsover", "Chesterfield", "Derbyshire Dales", "Erewash",
    "High Peak", "North East Derbyshire", "South Derbyshire",
    "Blaby", "Charnwood", "Harborough", "Hinckley and Bosworth", "Melton",
    "North West Leicestershire", "Oadby and Wigston",
    "Ashfield", "Bassetlaw", "Broxtowe", "Gedling", "Mansfield",
    "Newark and Sherwood", "Rushcliffe",
}
present = sorted(set(full[la_col].unique()) & target_districts)
missing = sorted(target_districts - set(full[la_col].unique()))
print(f"\n{len(present)} of {len(target_districts)} target districts found in the data:")
print(present)
print("\nMissing (name mismatch likely):", missing)
