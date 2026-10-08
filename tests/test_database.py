import importlib

import pytest
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor

from apps.warehouse.models import Reading
from tests.factories import ReadingFactory

pytestmark = [pytest.mark.django_db, pytest.mark.integration]


def test_fresh_migrations_and_extensions():
    # pytest-django creates a fresh PostgreSQL DB and applies every migration.
    executor = MigrationExecutor(connection)
    assert not executor.migration_plan(executor.loader.graph.leaf_nodes())
    with connection.cursor() as cursor:
        cursor.execute("SHOW server_version_num")
        assert 160000 <= int(cursor.fetchone()[0]) < 170000
        cursor.execute("SELECT extname, extversion FROM pg_extension")
        extensions = dict(cursor.fetchall())
    for name in ("postgis", "timescaledb", "vector"):
        assert extensions.get(name)


@pytest.mark.parametrize(
    "table,column",
    [
        ("warehouse_reading", "observed_at"),
        ("warehouse_weatherobservation", "observed_at"),
        ("warehouse_firedetection", "detected_at"),
    ],
)
def test_hypertables_and_unique_indexes(table, column):
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT hypertable_name FROM timescaledb_information.hypertables "
            "WHERE hypertable_name = %s",
            [table],
        )
        assert cursor.fetchone() == (table,)
        cursor.execute(
            """
            SELECT array_agg(a.attname)
            FROM pg_index i JOIN pg_attribute a
              ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey::smallint[])
            WHERE i.indrelid = %s::regclass AND i.indisunique
            GROUP BY i.indexrelid
        """,
            [table],
        )
        unique_columns = cursor.fetchall()
    assert unique_columns
    assert all(column in columns for (columns,) in unique_columns)


def test_duplicate_reading_is_rejected():
    reading = ReadingFactory()
    with pytest.raises(IntegrityError), transaction.atomic():
        Reading.objects.create(
            station=reading.station,
            pollutant=reading.pollutant,
            observed_at=reading.observed_at,
            value=1,
            raw_value=1,
            ingestion_run=reading.ingestion_run,
        )


def test_missing_and_negative_measurements_remain_auditable():
    missing = ReadingFactory(value=None, raw_value=None, quality_flag="missing")
    negative = ReadingFactory(value=None, raw_value=-1, quality_flag="negative")
    assert missing.value is None
    assert negative.raw_value == -1
    with pytest.raises(IntegrityError), transaction.atomic():
        ReadingFactory(value=None, quality_flag="ok")


@pytest.mark.django_db(transaction=True)
def test_reverse_hypertable_migration_preserves_rows_and_keys():
    reading = ReadingFactory()
    original_pk = reading.pk
    migration = importlib.import_module("apps.warehouse.migrations.0002_hypertables")
    executor = MigrationExecutor(connection)
    try:
        executor.migrate([("warehouse", "0001_initial")])
        assert Reading.objects.get(pk=original_pk).value == reading.value
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT count(*) FROM timescaledb_information.hypertables "
                "WHERE hypertable_name = 'warehouse_reading'"
            )
            assert cursor.fetchone()[0] == 0
        # The reverse SQL preserves the unique key, even on the ordinary table.
        test_duplicate_reading_is_rejected()
    finally:
        MigrationExecutor(connection).migrate([("warehouse", "0002_hypertables")])
    assert Reading.objects.get(pk=original_pk).value == reading.value
    assert migration.Migration.operations[0].reversible
