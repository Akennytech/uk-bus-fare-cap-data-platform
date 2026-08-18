# Bronze layer

Raw, immutable, as-landed data lives in MinIO (bucket `bronze`), not in this
folder — this directory just documents the landing convention so the
partitioning scheme is discoverable from the repo without needing MinIO
running.

## Path convention

```
bronze/{source_name}/dt={YYYY-MM-DD}/{filename}
```

Examples:

```
bronze/naptan/dt=2026-08-15/naptan_stops.csv
bronze/bods/dt=2026-08-15/dataset_catalogue.json
bronze/open_meteo/dt=2026-08-15/manchester_2025-01-01_2025-12-31.json
```

## Rules

- Bronze files are never edited or overwritten in place — each run lands a
  new dated partition.
- No transformation happens here beyond byte-for-byte landing of the source
  response. All cleaning happens in the PySpark Bronze -> Silver jobs
  (see `spark/`).
- Bronze is the audit trail: if a downstream number ever looks wrong, this is
  where you go to see exactly what the source returned on that date.
