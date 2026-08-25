"""Clean/summarize BODS TransXChange timetable zips from Bronze into Silver.

Deliberately NOT PySpark: XML parsing doesn't parallelize well at this data
volume (78 files, low hundreds of MB total), and using plain Python avoids
reintroducing the Java/Hadoop dependency chain for no benefit.

Real-world wrinkle discovered on the first run: BODS dataset metadata says
extension="zip" for every dataset, but a meaningful share of operators'
publishing tools (smaller operators especially) actually upload raw,
un-zipped TransXChange XML directly. So this script sniffs the real content
(zip magic bytes vs raw "<?xml") rather than trusting the metadata field.

Scope decision (documented like ADR-001 in documentation/data_dictionary.md):
TransXChange fully resolved would mean journey patterns, ordered stop
sequences, and calendar exceptions. This pass extracts a service-level
summary instead: for each (dataset, operator, line) we count VehicleJourney
elements as a scheduled_trips proxy, and record the raw day-pattern tags
found in each journey's OperatingProfile rather than resolving them into an
actual calendar.

Run: python spark/clean_bods.py
"""
from __future__ import annotations

import io
import logging
import sys
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[1] / "ingestion"))
from common.config import settings  # noqa: E402
from common.storage import get_client  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("clean_bods")


def find_latest_bods_timetable_objects(client) -> list:
    prefix = "bods_timetables/"
    objects = list(client.list_objects(settings.bucket_bronze, prefix=prefix, recursive=True))
    if not objects:
        raise SystemExit(f"No objects found under {prefix} in bucket {settings.bucket_bronze}")
    dts = sorted({o.object_name.split("/")[1] for o in objects if "/" in o.object_name})
    latest_dt = dts[-1]
    latest = [o for o in objects if f"/{latest_dt}/" in o.object_name]
    log.info("Using partition %s: %d files", latest_dt, len(latest))
    return latest


def text_of(elem, tag):
    child = elem.find(f"{{*}}{tag}")
    return child.text.strip() if child is not None and child.text else None


def parse_transxchange(xml_bytes: bytes, dataset_id: str) -> list[dict]:
    root = ET.fromstring(xml_bytes)

    operators = {}
    for tag in ("Operator", "LicensedOperator"):
        for op in root.findall(f".//{{*}}Operators/{{*}}{tag}"):
            op_id = op.get("id")
            operators[op_id] = {
                "noc": text_of(op, "NationalOperatorCode"),
                "name": text_of(op, "OperatorShortName") or text_of(op, "TradingName"),
            }

    services = {}
    for svc in root.findall(".//{*}Services/{*}Service"):
        service_code = text_of(svc, "ServiceCode")
        op_ref = text_of(svc, "RegisteredOperatorRef")
        op_period = svc.find("{*}OperatingPeriod")
        start_date = text_of(op_period, "StartDate") if op_period is not None else None
        end_date = text_of(op_period, "EndDate") if op_period is not None else None
        std = svc.find("{*}StandardService")
        origin = text_of(std, "Origin") if std is not None else None
        destination = text_of(std, "Destination") if std is not None else None
        lines = {}
        for line in svc.findall(".//{*}Lines/{*}Line"):
            lines[line.get("id")] = text_of(line, "LineName")
        services[service_code] = {
            "operator_ref": op_ref,
            "start_date": start_date,
            "end_date": end_date,
            "origin": origin,
            "destination": destination,
            "lines": lines,
        }

    counts: dict[tuple, dict] = {}
    for vj in root.findall(".//{*}VehicleJourneys/{*}VehicleJourney"):
        service_ref = text_of(vj, "ServiceRef")
        line_ref = text_of(vj, "LineRef")
        if not service_ref:
            continue
        day_tags = []
        op_profile = vj.find("{*}OperatingProfile")
        if op_profile is not None:
            days_elem = op_profile.find(".//{*}RegularDayType/{*}DaysOfWeek")
            if days_elem is not None:
                day_tags = [child.tag.split("}")[-1] for child in days_elem]
        days_str = "+".join(day_tags) if day_tags else "unspecified"

        key = (dataset_id, service_ref, line_ref, days_str)
        counts.setdefault(key, {"scheduled_trips": 0})
        counts[key]["scheduled_trips"] += 1

    rows = []
    for (ds_id, service_ref, line_ref, days_str), agg in counts.items():
        svc = services.get(service_ref, {})
        op_ref = svc.get("operator_ref")
        op_info = operators.get(op_ref, {})
        line_name = svc.get("lines", {}).get(line_ref) or line_ref
        rows.append(
            {
                "dataset_id": ds_id,
                "operator_noc": op_info.get("noc"),
                "operator_name": op_info.get("name"),
                "service_code": service_ref,
                "line_name": line_name,
                "origin": svc.get("origin"),
                "destination": svc.get("destination"),
                "start_date": svc.get("start_date"),
                "end_date": svc.get("end_date"),
                "days_of_week": days_str,
                "scheduled_trips": agg["scheduled_trips"],
            }
        )
    return rows


def main() -> None:
    client = get_client()
    file_objects = find_latest_bods_timetable_objects(client)

    all_rows: list[dict] = []
    files_ok, files_failed, xml_failed = 0, 0, 0
    raw_xml_count, zip_count = 0, 0

    for obj in file_objects:
        filename = obj.object_name.rsplit("/", 1)[-1]
        dataset_id = filename.split("_", 1)[0]
        try:
            resp = client.get_object(settings.bucket_bronze, obj.object_name)
            content_bytes = resp.read()
            resp.close()
            resp.release_conn()
        except Exception as exc:  # noqa: BLE001
            log.warning("Failed to download %s: %s", obj.object_name, exc)
            files_failed += 1
            continue

        try:
            if zipfile.is_zipfile(io.BytesIO(content_bytes)):
                zip_count += 1
                with zipfile.ZipFile(io.BytesIO(content_bytes)) as zf:
                    xml_names = [n for n in zf.namelist() if n.lower().endswith(".xml")]
                    for xml_name in xml_names:
                        try:
                            xml_bytes = zf.read(xml_name)
                            all_rows.extend(parse_transxchange(xml_bytes, dataset_id))
                        except ET.ParseError as exc:
                            log.warning("XML parse error in %s (%s): %s", filename, xml_name, exc)
                            xml_failed += 1
            else:
                # Metadata says extension="zip" but this operator's publishing
                # tool actually uploaded raw, un-zipped TransXChange XML.
                raw_xml_count += 1
                try:
                    all_rows.extend(parse_transxchange(content_bytes, dataset_id))
                except ET.ParseError as exc:
                    log.warning("XML parse error in %s (raw XML): %s", filename, exc)
                    xml_failed += 1
            files_ok += 1
        except Exception as exc:  # noqa: BLE001
            log.warning("Failed to process %s (%d bytes): %s", filename, len(content_bytes), exc)
            files_failed += 1

        log.info("Processed %s (dataset %s) -- running row total: %d", filename, dataset_id, len(all_rows))

    log.info(
        "Files processed OK: %d (of which %d zips, %d raw XML), failed: %d, XML parse errors: %d",
        files_ok, zip_count, raw_xml_count, files_failed, xml_failed,
    )

    if not all_rows:
        raise SystemExit("No rows extracted -- check the warnings above.")

    df = pd.DataFrame(all_rows)
    before = len(df)
    df = df.dropna(subset=["operator_name", "line_name"])
    after = len(df)
    log.info(
        "BODS: extracted %d (operator, line, day-pattern) rows, kept %d after dropping unresolved operator/line (%d dropped)",
        before, after, before - after,
    )

    local_out = str(Path(tempfile.gettempdir()) / "bods_services_clean.csv")
    df.to_csv(local_out, index=False)

    object_name = "bods/services/bods_services_clean.csv"
    client.fput_object(settings.bucket_silver, object_name, local_out)
    log.info("Uploaded %d cleaned rows to s3://%s/%s", after, settings.bucket_silver, object_name)


if __name__ == "__main__":
    main()
