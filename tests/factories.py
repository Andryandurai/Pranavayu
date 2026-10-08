import hashlib

import factory
from django.contrib.gis.geos import Point
from django.utils import timezone

from apps.ingest.models import DataSource, IngestionRun
from apps.rag.models import Document
from apps.warehouse.models import City, Pollutant, Reading, State, Station


class StateFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = State

    name = factory.Sequence(lambda n: f"Test state {n}")
    code = factory.Sequence(lambda n: f"T{n}")


class CityFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = City

    name = factory.Sequence(lambda n: f"Test city {n}")
    slug = factory.Sequence(lambda n: f"test-city-{n}")
    state = factory.SubFactory(StateFactory)
    location = factory.LazyFunction(lambda: Point(77.2, 28.6, srid=4326))


class DataSourceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DataSource

    name = factory.Sequence(lambda n: f"Test source {n}")
    slug = factory.Sequence(lambda n: f"test-source-{n}")
    url = "https://example.com/test-data"


class StationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Station

    external_id = factory.Sequence(lambda n: f"test-station-{n}")
    name = factory.Sequence(lambda n: f"Test station {n}")
    source = factory.SubFactory(DataSourceFactory)
    city = factory.SubFactory(CityFactory)
    location = factory.LazyFunction(lambda: Point(77.2, 28.6, srid=4326))


class PollutantFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Pollutant
        django_get_or_create = ["code"]

    code = "pm25"
    display_name = "PM2.5"
    unit = "µg/m³"


class IngestionRunFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = IngestionRun

    source = factory.SubFactory(DataSourceFactory)
    task_name = "tests.fixture"
    started_at = factory.LazyFunction(timezone.now)


class ReadingFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Reading

    station = factory.SubFactory(StationFactory)
    pollutant = factory.SubFactory(PollutantFactory)
    observed_at = factory.LazyFunction(timezone.now)
    value = 12.5
    raw_value = 12.5
    ingestion_run = factory.LazyAttribute(
        lambda obj: IngestionRunFactory(source=obj.station.source)
    )


class DocumentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Document

    title = factory.Sequence(lambda n: f"Test document {n}")
    file = "documents/test.pdf"
    sha256 = factory.Sequence(lambda n: hashlib.sha256(f"test-{n}".encode()).hexdigest())
    page_count = 5
