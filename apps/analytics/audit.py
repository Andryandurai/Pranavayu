import csv
import json
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

from django.db import connection, transaction

from apps.ingest.http import RawCache
from apps.ingest.quality import QUALITY_RULE_VERSION, flag_readings
from apps.ingest.sources.air import ALIASES
from apps.ingest.units import number
from apps.warehouse.models import Reading, Station

from .models import ReadingFlagChange, StationEligibility

UNVERIFIED = {"site_292", "site_293", "site_5405", "site_5618", "site_5767"}
QUALITY_VERSION = QUALITY_RULE_VERSION


def exclude_unverified():
    for station in Station.objects.filter(external_id__in=UNVERIFIED):
        existing = StationEligibility.objects.filter(station=station).first()
        if existing and existing.evidence.get("verified_official_listing"):
            continue
        StationEligibility.objects.update_or_create(
            station=station,
            defaults={
                "excluded_from_city": True,
                "excluded_from_spatial": True,
                "reason": "Primary registry GPS unavailable; contributed coordinates unverified.",
                "evidence": {"coordinate_source": "Zeel/C1", "verified_official_listing": False},
            },
        )
    return list(
        StationEligibility.objects.filter(excluded_from_city=True).values(
            "station_id", "station__external_id", "station__name", "reason"
        )
    )


def flag_breakdown():
    with connection.cursor() as cursor:
        cursor.execute("""SELECT d.slug,r.quality_flag,p.code,r.station_id,s.name,
            extract(year FROM r.observed_at AT TIME ZONE 'Asia/Kolkata')::int,count(*)
            FROM warehouse_reading r JOIN warehouse_station s ON s.id=r.station_id
            JOIN ingest_datasource d ON d.id=s.source_id
            JOIN warehouse_pollutant p ON p.id=r.pollutant_id
            GROUP BY d.slug,r.quality_flag,p.code,r.station_id,s.name,6
            ORDER BY d.slug,r.quality_flag,p.code,r.station_id,6""")
        keys = ["source", "flag", "pollutant", "station", "station_name", "year", "rows"]
        rows = [dict(zip(keys, row, strict=True)) for row in cursor.fetchall()]
    totals = defaultdict(lambda: defaultdict(int))
    for row in rows:
        totals[row["source"]][row["flag"]] += row["rows"]
    return {"breakdown": rows, "totals": dict(totals)}


def measurement_fingerprint():
    with connection.cursor() as cursor:
        cursor.execute("""SELECT count(*),bit_xor(hashtextextended(concat_ws('|',station_id,
            pollutant_id,observed_at AT TIME ZONE 'UTC',raw_value,value,ingestion_run_id),0))
            FROM warehouse_reading""")
        count, digest = cursor.fetchone()
    return {"rows": count, "order_independent_record_hash": digest}


def quarter_evidence():
    """Inspect cached original quarters for positive flatline candidates, without HTTP."""
    candidates = defaultdict(set)
    for station, code, time in (
        Reading.objects.filter(quality_flag="stuck", value__gt=0, station__source__slug="opencity")
        .values_list("station_id", "pollutant__code", "observed_at")
        .iterator(chunk_size=5000)
    ):
        candidates[station].add((code, time))
    # Cleared candidates remain auditable. Re-examine them on subsequent runs
    # so lack of a current stuck flag cannot discard the evidence that cleared it.
    for station, code, time in (
        ReadingFlagChange.objects.filter(old_flag="stuck", station__source__slug="opencity")
        .values_list("station_id", "pollutant__code", "observed_at")
        .distinct()
    ):
        candidates[station].add((code, time))
    stations = dict(
        Station.objects.filter(source__slug="opencity").values_list("external_id", "id")
    )
    evidence, files = {}, []
    cache = RawCache()
    for path in sorted(cache.root.glob("opencity/*/*.csv")):
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames or "Timestamp" not in reader.fieldnames:
                continue
            first = next((r for r in reader if r.get("Station ID")), None)
            if not first:
                continue
            station_id = stations.get(first["Station ID"])
            if station_id not in candidates:
                continue
        _, manifest = cache.local(path)
        slots = defaultdict(dict)
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            columns = {k: ALIASES.get(k.lower().split(" (")[0]) for k in reader.fieldnames}
            for row in reader:
                text = row.get("Timestamp")
                if not text:
                    continue
                instant = datetime.fromisoformat(text).astimezone(UTC)
                hour = instant.replace(minute=0, second=0, microsecond=0)
                for column, code in columns.items():
                    if (code, hour) in candidates[station_id]:
                        slots[(code, hour)][instant.minute] = number(row.get(column))
        for (code, hour), values in slots.items():
            valid = [v for v in values.values() if v is not None and v >= 0]
            evidence.setdefault(
                (station_id, code, hour),
                {
                    "varies": len(set(valid)) > 1,
                    "valid_quarters": len(valid),
                    "minimum": min(valid) if valid else None,
                    "maximum": max(valid) if valid else None,
                    "file": manifest["path"],
                    "sha256": manifest["sha256"],
                },
            )
        files.append(manifest["path"])
    return evidence, files


def reflag(run, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    before = flag_breakdown()
    fingerprint = measurement_fingerprint()
    evidence, files = quarter_evidence()
    changed_count = 0
    with (output / "quarter_flag_evidence.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "station",
                "pollutant",
                "hour",
                "varies",
                "valid_quarters",
                "minimum",
                "maximum",
                "file",
                "sha256",
            ],
        )
        writer.writeheader()
        for (station, code, time), item in sorted(evidence.items()):
            writer.writerow(
                {"station": station, "pollutant": code, "hour": time.isoformat(), **item}
            )
    for station in Station.objects.all():
        records = list(
            Reading.objects.filter(station=station).values(
                "station_id",
                "pollutant_id",
                "pollutant__code",
                "observed_at",
                "value",
                "raw_value",
                "quality_flag",
            )
        )
        for record in records:
            record["code"] = record.pop("pollutant__code")
            record["old_flag"] = record["quality_flag"]
            record["quarter_varies"] = evidence.get(
                (station.pk, record["code"], record["observed_at"]), {}
            ).get("varies", False)
        flag_readings(records)
        changed = [r for r in records if r["old_flag"] != r["quality_flag"]]
        for offset in range(0, len(changed), 1000):
            batch = changed[offset : offset + 1000]
            placeholders = ",".join(["(%s,%s,%s::timestamptz,%s)"] * len(batch))
            params = [
                v
                for r in batch
                for v in (r["station_id"], r["pollutant_id"], r["observed_at"], r["quality_flag"])
            ]
            with transaction.atomic(), connection.cursor() as cursor:
                cursor.execute(
                    f"""UPDATE warehouse_reading r SET quality_flag=v.flag
                    FROM (VALUES {placeholders}) v(station,pollutant,observed,flag)
                    WHERE r.station_id=v.station AND r.pollutant_id=v.pollutant
                      AND r.observed_at=v.observed""",
                    params,
                )
                ReadingFlagChange.objects.bulk_create(
                    [
                        ReadingFlagChange(
                            run=run,
                            station_id=r["station_id"],
                            pollutant_id=r["pollutant_id"],
                            observed_at=r["observed_at"],
                            old_flag=r["old_flag"],
                            new_flag=r["quality_flag"],
                        )
                        for r in batch
                    ]
                )
            changed_count += len(batch)
        if changed:
            print(
                json.dumps(
                    {"event": "station_reflagged", "station": station.pk, "changed": len(changed)}
                ),
                flush=True,
            )
    after_fingerprint = measurement_fingerprint()
    if fingerprint != after_fingerprint:
        raise RuntimeError("Measurement/provenance fingerprint changed during flag-only update")
    result = {
        "version": QUALITY_VERSION,
        "before": before,
        "after": flag_breakdown(),
        "changed_rows": changed_count,
        "fingerprint_before": fingerprint,
        "fingerprint_after": after_fingerprint,
        "quarter_candidates_examined": len(evidence),
        "varying_quarter_candidates": sum(r["varies"] for r in evidence.values()),
        "cached_files_examined": files,
        "excluded_stations": exclude_unverified(),
    }
    (output / "flag_audit.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    for label in ["before", "after"]:
        rows = result[label]["breakdown"]
        with (output / f"flags_{label}.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle, fieldnames=list(rows[0]) if rows else ["source", "flag", "rows"]
            )
            writer.writeheader()
            writer.writerows(rows)
    return result
