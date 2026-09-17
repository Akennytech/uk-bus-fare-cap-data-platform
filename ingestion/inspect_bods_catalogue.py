"""One-off: pull today's BODS dataset catalogue back out of Bronze and summarize it."""
import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))
from common.config import settings
from common.storage import get_client

client = get_client()
prefix = "bods/"
objects = list(client.list_objects(settings.bucket_bronze, prefix=prefix, recursive=True))
if not objects:
    raise SystemExit(f"No objects found under {prefix} in bucket {settings.bucket_bronze}")

latest = max(objects, key=lambda o: o.object_name)
print(f"Reading {latest.object_name}")

resp = client.get_object(settings.bucket_bronze, latest.object_name)
data = json.loads(resp.read())
resp.close()
resp.release_conn()

if isinstance(data, dict):
    print("Top-level keys:", list(data.keys()))
    print("count:", data.get("count"))
    print("next:", data.get("next"))
    results = data.get("results", [])
    print(f"Datasets on this page: {len(results)}")
    for r in results[:3]:
        print(json.dumps(r, indent=2))
        print("---")
else:
    print("Unexpected response shape:", type(data))
    print(json.dumps(data, indent=2)[:3000])
