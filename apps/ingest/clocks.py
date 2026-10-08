"""Verified publisher-clock decoding and auditable, idempotent stored correction."""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from django.conf import settings
from django.db import connection, transaction
from django.utils import timezone

from .models import DataSource, IngestionRun
from .units import IST

CLOCK_VERSION = "opencity-ist-clock-v1"


def approved_clock(path, digest):
    catalog = Path(settings.BASE_DIR) / "docs/results/PHASE3B_CLOCK_INPUTS.json"
    if not catalog.exists():
        return False
    relative = Path(path).resolve().relative_to(Path(settings.RAW_DATA_ROOT).resolve()).as_posix()
    return json.loads(catalog.read_text())["approved_inputs"].get(relative) == digest


def published_ist_to_utc(timestamp):
    # These verified files attach UTC without converting the original IST clock.
    parsed = (
        timestamp
        if isinstance(timestamp, datetime)
        else datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
    )
    return parsed.replace(tzinfo=IST).astimezone(UTC)


def value_fingerprint():
    with connection.cursor() as cursor:
        cursor.execute("""SELECT count(*),bit_xor(hashtextextended(
            ROW(station_id,pollutant_id,value,raw_value,quality_flag,ingestion_run_id)::text,0))
            FROM warehouse_reading""")
        count, digest = cursor.fetchone()
    return dict(rows=count, values_flags_provenance_hash=digest)


def correct_stored_clocks():
    with transaction.atomic(), connection.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_xact_lock(7319021)")
        cursor.execute(
            """SELECT DISTINCT r.ingestion_run_id FROM warehouse_reading r
            JOIN warehouse_station s ON s.id=r.station_id
            JOIN ingest_datasource d ON d.id=s.source_id
            JOIN ingest_ingestionrun j ON j.id=r.ingestion_run_id
            WHERE d.slug='opencity' AND
            coalesce(j.params->>'timestamp_clock_version','')<>%s""",
            [CLOCK_VERSION],
        )
        ids = [row[0] for row in cursor.fetchall()]
        if not ids:
            return dict(status="already canonical", corrected_rows=0, version=CLOCK_VERSION)
        cursor.execute(
            """SELECT count(*) FROM warehouse_reading WHERE ingestion_run_id=ANY(%s)
            AND (extract(minute FROM observed_at AT TIME ZONE 'UTC')<>0
              OR extract(second FROM observed_at AT TIME ZONE 'UTC')<>0
              OR extract(year FROM observed_at AT TIME ZONE 'UTC') NOT IN (2024,2025))""",
            [ids],
        )
        if cursor.fetchone()[0]:
            raise ValueError("Pending rows do not match verified 2024-2025 UTC-labelled hour bins")
        before = value_fingerprint()
        cursor.execute(
            """UPDATE warehouse_reading SET observed_at=observed_at-interval '5h30m'
            WHERE ingestion_run_id=ANY(%s)""",
            [ids],
        )
        changed = cursor.rowcount
        cursor.execute("""UPDATE warehouse_station SET first_seen=first_seen-interval '5h30m',
            last_seen=last_seen-interval '5h30m' WHERE source_id=
            (SELECT id FROM ingest_datasource WHERE slug='opencity')""")
        cursor.execute("""UPDATE analytics_readingflagchange SET
            observed_at=observed_at-interval '5h30m' WHERE station_id IN
            (SELECT id FROM warehouse_station WHERE source_id=
             (SELECT id FROM ingest_datasource WHERE slug='opencity'))""")
        for job in IngestionRun.objects.filter(pk__in=ids):
            job.params["timestamp_clock_version"] = CLOCK_VERSION
            job.params["original_published_clock_recover_by_hours"] = 5.5
            job.save(update_fields=["params"])
        after = value_fingerprint()
        if before != after:
            raise RuntimeError("Clock correction changed values, flags, counts or ingestion links")
        proof = Path(settings.BASE_DIR) / "docs/results/PHASE3B_CLOCK_INPUTS.json"
        record = dict(
            corrected_rows=changed,
            ingestion_run_ids=ids,
            before=before,
            after=after,
            shift_hours=-5.5,
            original_label_recovery_hours=5.5,
            evidence_sha256=hashlib.sha256(proof.read_bytes()).hexdigest(),
        )
        audit = IngestionRun.objects.create(
            source=DataSource.objects.get(slug="opencity"),
            task_name="correct_stored_clocks",
            started_at=timezone.now(),
            finished_at=timezone.now(),
            status="success",
            rows_fetched=changed,
            params={**record, "timestamp_clock_version": CLOCK_VERSION},
        )
        return dict(status="canonicalized", audit_run=audit.pk, version=CLOCK_VERSION, **record)
