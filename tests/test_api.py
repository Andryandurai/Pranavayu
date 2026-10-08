import pytest

from tests.factories import CityFactory, PollutantFactory, StationFactory

pytestmark = [pytest.mark.django_db, pytest.mark.integration]


def test_health_reports_real_services(api_client):
    response = api_client.get("/api/health/")
    assert response.status_code == 200, response.json()
    report = response.json()
    assert report["ok"]
    for name in ("database", "redis", "celery"):
        assert report["checks"][name]["ok"]
    for name in ("postgis", "timescaledb", "vector"):
        assert report["checks"]["extensions"][name]["ok"]
        assert report["checks"]["extensions"][name]["version"]


def test_station_api_returns_paginated_geojson(api_client):
    station = StationFactory()
    response = api_client.get("/api/stations/")
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "FeatureCollection"
    assert data["count"] == 1
    feature = data["features"][0]
    assert feature["type"] == "Feature"
    assert feature["id"] == station.pk
    assert feature["geometry"] == {"type": "Point", "coordinates": [77.2, 28.6]}
    assert feature["properties"]["external_id"] == station.external_id
    assert "next" in data and "previous" in data
    assert api_client.post("/api/stations/", {}).status_code == 405


def test_city_geojson_and_pollutant_catalogue(api_client):
    city = CityFactory()
    pollutant = PollutantFactory()
    assert api_client.get("/api/cities/").json()["features"][0]["id"] == city.pk
    assert api_client.get("/api/pollutants/").json()["results"][0]["code"] == pollutant.code
    assert api_client.patch(f"/api/pollutants/{pollutant.pk}/", {}).status_code == 405
