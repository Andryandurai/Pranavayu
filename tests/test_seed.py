import pytest
from django.core.management import call_command

from apps.ingest.models import DataSource, IngestionRun
from apps.rag.models import Document, DocumentChunk
from apps.warehouse.models import (
    City,
    FireDetection,
    Pollutant,
    Reading,
    State,
    Station,
    WeatherObservation,
)

pytestmark = [pytest.mark.django_db, pytest.mark.integration]


def test_reference_seed_is_idempotent_and_creates_no_measurements():
    call_command("seed_reference")
    before = {
        model: list(model.objects.values_list("pk", flat=True))
        for model in (State, City, Pollutant, DataSource)
    }
    call_command("seed_reference")
    for model, pks in before.items():
        assert list(model.objects.values_list("pk", flat=True)) == pks
    assert City.objects.count() == 12
    assert State.objects.count() == 10
    assert Pollutant.objects.count() == 7
    assert DataSource.objects.count() == 12
    for model in (
        Station,
        Reading,
        WeatherObservation,
        FireDetection,
        IngestionRun,
        Document,
        DocumentChunk,
    ):
        assert model.objects.count() == 0
    assert Pollutant.objects.get(code="co").naaqs_24h_value is None
    assert Pollutant.objects.get(code="o3").who_averaging_hours == 8
    assert Pollutant.objects.get(code="nh3").who_guideline_value is None
    delhi = City.objects.get(slug="delhi")
    assert delhi.location.srid == 4326
    assert delhi.location.x == pytest.approx(77.2090)
    assert delhi.location.y == pytest.approx(28.6139)
    delhi.population = 123  # synthetic value exists only inside this test
    delhi.is_ncap_nonattainment = False
    delhi.save()
    call_command("seed_reference")
    delhi.refresh_from_db()
    assert delhi.population == 123
    assert not delhi.is_ncap_nonattainment
