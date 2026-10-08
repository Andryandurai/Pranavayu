from datetime import UTC, datetime

import pytest
from django.core.management import call_command

from apps.ingest.clocks import CLOCK_VERSION, correct_stored_clocks, published_ist_to_utc
from apps.ingest.models import DataSource
from apps.warehouse.models import City, Pollutant, Reading
from tests.factories import IngestionRunFactory, StationFactory


@pytest.mark.django_db
def test_stored_clock_repair_preserves_values_and_is_idempotent(tmp_path, settings):
    call_command("seed_reference", verbosity=0)
    settings.BASE_DIR = tmp_path
    (tmp_path / "docs/results").mkdir(parents=True)
    (tmp_path / "docs/results/PHASE3B_CLOCK_INPUTS.json").write_text("{}")
    source = DataSource.objects.create(slug="opencity", name="Clock fixture")
    run = IngestionRunFactory(source=source)
    station = StationFactory(source=source, city=City.objects.get(slug="delhi"))
    pollutant = Pollutant.objects.get(code="pm25")
    original = datetime(2024, 1, 1, tzinfo=UTC)
    Reading.objects.create(
        station=station,
        pollutant=pollutant,
        observed_at=original,
        value=42,
        raw_value=42,
        quality_flag="ok",
        ingestion_run=run,
    )
    boundary = datetime(2024, 1, 4, tzinfo=UTC)
    Reading.objects.create(
        station=station,
        pollutant=pollutant,
        observed_at=boundary,
        value=96,
        raw_value=96,
        quality_flag="ok",
        ingestion_run=run,
    )
    first = correct_stored_clocks()
    row = Reading.objects.filter(station=station).order_by("observed_at").first()
    assert first["corrected_rows"] == 2
    assert row.observed_at == datetime(2023, 12, 31, 18, 30, tzinfo=UTC)
    assert (row.value, row.raw_value, row.ingestion_run_id) == (42, 42, run.pk)
    assert Reading.objects.get(station=station, value=96).observed_at == datetime(
        2024, 1, 3, 18, 30, tzinfo=UTC
    )
    assert correct_stored_clocks()["corrected_rows"] == 0
    run.refresh_from_db()
    assert run.params["timestamp_clock_version"] == CLOCK_VERSION
    assert published_ist_to_utc("2024-01-01T00:00:00+0000") == row.observed_at
