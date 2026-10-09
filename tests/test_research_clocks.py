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


@pytest.mark.django_db
def test_verified_ingestion_uses_native_ist_hour_bins(tmp_path, settings):
    from apps.ingest.http import RawCache
    from apps.ingest.sources.opencity import OpenCitySource

    call_command("seed_reference", verbosity=0)
    settings.RAW_DATA_ROOT = tmp_path
    source = OpenCitySource(cache=RawCache(root=tmp_path))
    source.run = IngestionRunFactory(source=source.source)
    path = tmp_path / "quarters.csv"
    header = "Timestamp,Station ID,Station Name,City,Latitude,Longitude,PM2.5 (ug/m3)\n"
    path.write_text(
        header
        + "".join(
            f"2024-01-01T02:{minute:02d}:00+0000,clock-site,Clock site,Delhi,28.6,77.2,{value}\n"
            for minute, value in [(0, 10), (15, 20), (30, 30), (45, 40)]
        )
    )
    metadata = {"published_clock_timezone": "Asia/Kolkata"}
    source.load_csv(path, quarter=True, metadata=metadata)
    assert source.run.params["timestamp_clock_version"] == CLOCK_VERSION
    row = Reading.objects.get(station__external_id="clock-site")
    assert row.observed_at == datetime(2023, 12, 31, 20, 30, tzinfo=UTC)
    assert (row.value, row.raw_value) == (25, 25)
    source.load_csv(path, quarter=True, metadata=metadata)
    assert Reading.objects.filter(station__external_id="clock-site").count() == 1
