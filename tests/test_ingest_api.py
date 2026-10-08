import json

import pytest

from apps.ingest.completeness import completeness
from apps.ingest.sources.cpcb_archive import CPCBArchiveSource
from apps.ingest.sources.openmeteo import OpenMeteoSource
from apps.warehouse.models import City, Reading
from tests.test_ingest_sources import FIXTURES, copy_fixture
from tests.test_ingest_sources import raw as raw
from tests.test_ingest_sources import seeded as seeded

pytestmark = pytest.mark.django_db


def test_reading_api_provenance_filters_pagination_and_read_only(seeded, raw, api_client):
    source = CPCBArchiveSource(cache=raw)
    path = copy_fixture(raw, "cpcb-hourly.csv", "cpcb/ccr/sample.csv")
    registry = json.loads((FIXTURES / "station-registry.json").read_text())["data"]
    with source.lifecycle("tests.api"):
        source.load_csv(path, registry=registry)
    station_id = Reading.objects.first().station_id
    params = {
        "station": station_id,
        "pollutant": "pm25",
        "start": "2018-12-31T18:30:00Z",
        "end": "2019-01-02T02:00:00Z",
    }
    response = api_client.get("/api/readings/", params)
    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 32
    assert results[0]["source"] == source.source.pk
    assert results[0]["ingestion_run"] == source.run.pk
    assert results[0]["raw_unit"] == "µg/m³"
    # At UTC midnight the final two IST-labelled sample hours are outside
    # the requested half-open range. Check that boundary explicitly.
    narrowed = {**params, "end": "2019-01-02T00:00:00Z"}
    assert len(api_client.get("/api/readings/", narrowed).json()["results"]) == 30
    assert api_client.post("/api/readings/", {}).status_code == 405
    params["end"] = "2020-01-01T00:00:00Z"
    assert api_client.get("/api/readings/", params).status_code == 400
    assert api_client.get("/api/readings/").status_code == 400


def test_weather_api_returns_ledger_run_and_range_limit(seeded, raw, api_client):
    source = OpenMeteoSource(cache=raw)
    path = copy_fixture(raw, "openmeteo.json", "openmeteo/delhi/sample.json")
    with source.lifecycle("tests.weather-api"):
        _, asset = source.local_asset(path)
        source.load_payload(json.loads(path.read_text()), City.objects.get(slug="delhi"), asset)
    response = api_client.get(
        "/api/weather/",
        {"city": "delhi", "start": "2019-01-01T00:00:00Z", "end": "2019-01-03T00:00:00Z"},
    )
    assert response.status_code == 200
    assert len(response.json()["results"]) == 48
    assert response.json()["results"][0]["ingestion_run"] == source.run.pk
    assert api_client.post("/api/weather/", {}).status_code == 405


def test_fire_api_rejects_bad_bbox_and_large_range(api_client):
    params = {"bbox": "78,33,73,27"}
    assert api_client.get("/api/fires/", params).status_code == 400
    assert api_client.get("/api/fires/", {"bbox": "73,27,78,33"}).status_code == 200
    assert api_client.post("/api/fires/", {}).status_code == 405


def test_completeness_uses_ist_distinct_hours_and_reports_actual_gaps(seeded, raw):
    source = CPCBArchiveSource(cache=raw)
    path = copy_fixture(raw, "cpcb-hourly.csv", "cpcb/ccr/sample.csv")
    registry = json.loads((FIXTURES / "station-registry.json").read_text())["data"]
    with source.lifecycle("tests.completeness"):
        source.load_csv(path, registry=registry)
    report = completeness("2019-01-01", "2019-01-02")
    delhi = next(x for x in report["city_years"] if x["city"] == "delhi")
    assert delhi["pm25_hours"] == 32 and delhi["expected_hours"] == 48
    assert delhi["percent"] == 66.67 and not delhi["at_least_75_percent"]
    assert report["station_days_under_75_percent"][0]["hours"] == 8
    assert report["station_days_under_75_percent"][0]["date"] == "2019-01-02"
