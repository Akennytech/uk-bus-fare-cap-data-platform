"""One-off: pull the ONS population estimates workbook back out of Bronze
and print its sheet names plus a preview of each, to figure out which
sheet(s) hold local-authority-level detail.
"""
import sys
import tempfile
from pathlib import Path

import openpyxl

sys.path.append(str(Path(__file__).resolve().parent))
from common.config import settings
from common.storage import get_client

client = get_client()
prefix = "ons_population/"
objects = list(client.list_objects(settings.bucket_bronze, prefix=prefix, recursive=True))
if not objects:
    raise SystemExit(f"No objects found under {prefix}")
latest = max(objects, key=lambda o: o.object_name)
print(f"Reading {latest.object_name}")

local_path = str(Path(tempfile.gettempdir()) / "ons_mye_inspect.xlsx")
client.fget_object(settings.bucket_bronze, latest.object_name, local_path)

wb = openpyxl.load_workbook(local_path, read_only=True, data_only=True)
print("Sheet names:", wb.sheetnames)

for name in ["MYE1", "MYE2 - Persons"]:
    ws = wb[name]
    print(f"\n--- Sheet: {name} ---")
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i >= 10:
            break
        print(row)
