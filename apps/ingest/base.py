import json
import logging
from contextlib import contextmanager

from django.db import connection, transaction
from django.db.models.constants import OnConflict
from django.db.models.sql.subqueries import InsertQuery
from django.utils import timezone
from django.utils.functional import cached_property

from .http import RawCache, safe_url
from .models import DataSource, IngestionRun, ObservationProvenance, RawAsset

logger = logging.getLogger(__name__)


class SourceUnavailable(Exception):
    """Provider requires an unavailable credential or no supported inputs exist."""


def insert_batch(model, objects, return_fields=()):
    """One batched INSERT ON CONFLICT DO NOTHING, with actual inserted keys/counts."""
    if not objects:
        return []
    fields = [
        field
        for field in model._meta.local_concrete_fields
        if not field.generated and not (field.auto_created and field.primary_key)
    ]
    query = InsertQuery(model, on_conflict=OnConflict.IGNORE)
    query.insert_values(fields, objects, raw=False)
    compiler = query.get_compiler(connection=connection)
    returning = ", ".join(connection.ops.quote_name(field) for field in return_fields) or "1"
    results = []
    with connection.cursor() as cursor:
        for sql, params in compiler.as_sql():
            cursor.execute(f"{sql} RETURNING {returning}", params)
            results.extend(cursor.fetchall())
    return results


def insert_reading_batch(rows, pollutants, ingestion_run_id):
    """COPY scalar readings into staging, then count actual conflict-ignore insertions."""
    if not rows:
        return []
    columns = "station_id,pollutant_id,observed_at,value,raw_value,quality_flag,ingestion_run_id"
    with connection.cursor() as cursor:
        cursor.execute("""CREATE TEMP TABLE IF NOT EXISTS enviro_reading_stage (
            station_id bigint, pollutant_id bigint, observed_at timestamptz,
            value double precision, raw_value double precision, quality_flag varchar(15),
            ingestion_run_id bigint) ON COMMIT DELETE ROWS""")
    with transaction.atomic(), connection.cursor() as cursor:
        cursor.execute("TRUNCATE enviro_reading_stage")
        with cursor.cursor.copy(f"COPY enviro_reading_stage ({columns}) FROM STDIN") as copier:
            for row in rows:
                copier.write_row(
                    (
                        row["station_id"],
                        pollutants[row["code"]],
                        row["observed_at"],
                        row["value"],
                        row["raw_value"],
                        row["quality_flag"],
                        ingestion_run_id,
                    )
                )
        cursor.execute(f"""INSERT INTO warehouse_reading ({columns})
            SELECT {columns} FROM enviro_reading_stage ON CONFLICT DO NOTHING
            RETURNING station_id,pollutant_id,observed_at,quality_flag""")
        return cursor.fetchall()


class Source:
    slug = ""
    name = ""
    url = ""
    licence = ""
    access_method = "download"

    def __init__(self, cache=None):
        self.cache = cache or RawCache()
        self.run = None
        self.errors = []

    @cached_property
    def source(self):
        source, _ = DataSource.objects.get_or_create(
            slug=self.slug,
            defaults={
                "name": self.name,
                "url": self.url,
                "licence": self.licence,
                "access_method": self.access_method,
            },
        )
        return source

    def event(self, event, **values):
        logger.info(
            json.dumps(
                {
                    "event": event,
                    "source": self.slug,
                    "run_id": self.run.pk if self.run else None,
                    **values,
                },
                default=str,
            )
        )

    @contextmanager
    def lifecycle(self, task_name, params=None):
        self.errors = []
        self.run = IngestionRun.objects.create(
            source=self.source,
            task_name=task_name,
            started_at=timezone.now(),
            params=json.loads(json.dumps(params or {}, default=str)),
        )
        self.event("run_started", task=task_name)
        try:
            yield self.run
        except SourceUnavailable as exc:
            self.run.status = IngestionRun.Status.SKIPPED
            self.run.error_message = safe_url(str(exc))
            self.event("run_skipped", reason=self.run.error_message)
        except (KeyboardInterrupt, SystemExit):
            self.run.status = (
                IngestionRun.Status.PARTIAL
                if self.run.rows_inserted
                else IngestionRun.Status.FAILED
            )
            self.run.error_message = (
                "Interrupted; verified raw cache and committed batches are retained."
            )
            raise
        except Exception as exc:
            self.run.status = (
                IngestionRun.Status.PARTIAL
                if self.run.rows_inserted
                else IngestionRun.Status.FAILED
            )
            self.run.error_message = safe_url(f"{type(exc).__name__}: {exc}")[:8000]
            self.event("run_failed", reason=self.run.error_message)
        else:
            self.run.status = (
                IngestionRun.Status.PARTIAL if self.errors else IngestionRun.Status.SUCCESS
            )
            self.run.error_message = "\n".join(self.errors)[:8000]
        finally:
            self.run.finished_at = timezone.now()
            self.run.save()
            self.event(
                "run_finished",
                status=self.run.status,
                rows_fetched=self.run.rows_fetched,
                rows_inserted=self.run.rows_inserted,
                rows_flagged=self.run.rows_flagged,
            )

    def execute(self, action, **options):
        with self.lifecycle(f"ingest.{self.slug}.{action}", options):
            getattr(self, action)(**options)
        return self.run

    def fail_asset(self, path, exc):
        message = safe_url(f"{path}: {type(exc).__name__}: {exc}")
        self.errors.append(message)
        self.event("asset_failed", path=str(path), reason=message)

    def register_asset(self, path, manifest):
        asset, _ = RawAsset.objects.get_or_create(
            source=self.source,
            sha256=manifest["sha256"],
            defaults={
                "ingestion_run": self.run,
                "path": str(path.relative_to(self.cache.root)),
                "size_bytes": manifest["size_bytes"],
                "download_url": manifest.get("url", ""),
                "licence": manifest.get("metadata", {}).get("licence") or self.licence,
                "metadata": manifest.get("metadata", {}),
            },
        )
        return asset

    def download_asset(self, url, relative, **kwargs):
        path, manifest = self.cache.download(url, relative, **kwargs)
        return path, self.register_asset(path, manifest)

    def local_asset(self, path, **metadata):
        path, manifest = self.cache.local(path, metadata)
        return path, self.register_asset(path, manifest)

    def insert_observations(self, model, objects, kind, asset, metadata=None):
        with transaction.atomic():
            inserted = insert_batch(
                model, objects, ("id", "observed_at" if kind == "weather" else "detected_at")
            )
            provenance = [
                ObservationProvenance(
                    kind=kind,
                    record_id=identifier,
                    observed_at=timestamp,
                    source=self.source,
                    ingestion_run=self.run,
                    asset=asset,
                    metadata=(metadata or {}).get(identifier, {}),
                )
                for identifier, timestamp in inserted
            ]
            insert_batch(ObservationProvenance, provenance)
        self.run.rows_inserted += len(inserted)
        self.run.rows_flagged += sum(
            bool((metadata or {}).get(identifier, {}).get("invalid_values"))
            for identifier, _ in inserted
        )
        self.run.save(
            update_fields=["rows_fetched", "rows_inserted", "rows_flagged", "params", "updated_at"]
        )
        return len(inserted)
