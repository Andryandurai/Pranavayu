import json
import shutil
from pathlib import Path

import pytest
import responses
from django.core.management import call_command

from apps.ingest.base import Source
from apps.ingest.http import HttpClient, RawCache, digest_file, safe_url
from apps.ingest.models import IngestionRun, ObservationProvenance, RawAsset
from apps.ingest.sources.air import REGISTRY_URL
from apps.ingest.sources.boundaries import BoundarySource
from apps.ingest.sources.cpcb_archive import CPCBArchiveSource
from apps.ingest.sources.era5 import ERA5Source
from apps.ingest.sources.firms import FIRMSsource
from apps.ingest.sources.openaq import OpenAQSource
from apps.ingest.sources.opencity import OpenCitySource
from apps.ingest.sources.openmeteo import OpenMeteoSource
from apps.ingest.tasks import configure_schedules
from apps.warehouse.models import City, FireDetection, Reading, Station, WeatherObservation

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def external_http():
    # Every external request in these source tests must have an explicit fixture.
    with responses.RequestsMock(assert_all_requests_are_fired=False) as mock:
        yield mock


@pytest.fixture
def raw(tmp_path, settings):
    settings.RAW_DATA_ROOT = tmp_path
    settings.INGEST_REQUEST_PAUSE = 0
    return RawCache(root=tmp_path)


@pytest.fixture
def seeded(db):
    call_command("seed_reference", verbosity=0)


def copy_fixture(raw, filename, relative):
    target = raw.path(relative)
    shutil.copyfile(FIXTURES / filename, target)
    return target


def registry_fixture(external_http):
    external_http.get(
        REGISTRY_URL, json=json.loads((FIXTURES / "station-registry.json").read_text())
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "source_class,filename,relative,quarter",
    [
        (CPCBArchiveSource, "cpcb-hourly.csv", "cpcb/ccr/sample.csv", False),
        (OpenCitySource, "opencity-delhi.csv", "opencity/delhi/sample.csv", True),
        (OpenCitySource, "opencity-bengaluru.csv", "opencity/bengaluru/sample.csv", True),
    ],
)
def test_real_air_samples_are_idempotent(seeded, raw, source_class, filename, relative, quarter):
    path = copy_fixture(raw, filename, relative)
    registry = json.loads((FIXTURES / "station-registry.json").read_text())["data"]
    source = source_class(cache=raw)
    with source.lifecycle("tests.real-air"):
        source.load_csv(path, registry=registry, quarter=quarter)
    assert source.run.status == "success", source.run.error_message
    assert source.run.rows_inserted > 0
    first_count = Reading.objects.count()
    station_count = Station.objects.count()
    assert not Reading.objects.exclude(station__source=source.source).exists()
    with source.lifecycle("tests.real-air-again"):
        source.load_csv(path, registry=registry, quarter=quarter)
    assert source.run.rows_inserted == source.run.rows_flagged == 0
    assert Reading.objects.count() == first_count
    assert Station.objects.count() == station_count
    assert RawAsset.objects.count() == 1


@pytest.mark.django_db
def test_weather_real_response_and_provenance_are_idempotent(seeded, raw):
    source = OpenMeteoSource(cache=raw)
    path = copy_fixture(raw, "openmeteo.json", "openmeteo/delhi/sample.json")
    city = City.objects.get(slug="delhi")
    for iteration in range(2):
        with source.lifecycle("tests.weather"):
            _, asset = source.local_asset(path)
            source.load_payload(json.loads(path.read_text()), city, asset)
        assert source.run.status == "success", source.run.error_message
        assert source.run.rows_inserted == (48 if iteration == 0 else 0)
    assert WeatherObservation.objects.count() == ObservationProvenance.objects.count() == 48
    assert all(x.boundary_layer_height_m is None for x in WeatherObservation.objects.all())
    provenance = ObservationProvenance.objects.first()
    assert provenance.asset_id == asset.pk and "dew_point_2m_c" in provenance.metadata


@pytest.mark.django_db
def test_firms_published_real_sample_utc_confidence_and_idempotency(seeded, raw):
    path = copy_fixture(raw, "firms.csv", "firms/sample.csv")
    source = FIRMSsource(cache=raw)
    for iteration in range(2):
        with source.lifecycle("tests.firms"):
            source.load_csv(path)
        assert source.run.status == "success", source.run.error_message
        assert source.run.rows_inserted == (5 if iteration == 0 else 0)
    assert FireDetection.objects.count() == ObservationProvenance.objects.count() == 5
    first = FireDetection.objects.order_by("detected_at").first()
    assert first.detected_at.hour == 6 and first.detected_at.minute == 31
    assert first.confidence == "n" and first.frp == 2.24


@pytest.mark.django_db
@pytest.mark.parametrize(
    "source_class,env_name",
    [(OpenAQSource, "OPENAQ_API_KEY"), (FIRMSsource, "FIRMS_MAP_KEY"), (ERA5Source, "CDS_API_KEY")],
)
def test_missing_keys_skip_without_error_or_http(
    seeded, raw, monkeypatch, external_http, source_class, env_name
):
    monkeypatch.delenv(env_name, raising=False)
    run = source_class(cache=raw).execute("load")
    assert run.status == "skipped" and run.error_message == "skipped: no key"
    assert run.finished_at is not None and run.rows_inserted == 0
    assert len(external_http.calls) == 0


@pytest.mark.django_db
def test_openaq_v3_contract_with_real_cpcb_values(seeded, raw, monkeypatch, external_http):
    monkeypatch.setenv("OPENAQ_API_KEY", "fixture-token")
    # This is explicitly a schema-adapted real CPCB sample, not an authenticated
    # OpenAQ capture; its provenance is recorded in fixtures/manifest.json.
    City.objects.exclude(slug="delhi").delete()
    external_http.get(
        "https://api.openaq.org/v3/locations",
        json=json.loads((FIXTURES / "openaq-locations.json").read_text()),
    )
    external_http.get(
        "https://api.openaq.org/v3/sensors/1031/hours",
        json=json.loads((FIXTURES / "openaq-hours.json").read_text()),
    )
    source = OpenAQSource(cache=raw)
    first = source.execute("load", start="2019-01-01", end="2019-01-02")
    assert first.status == "success", first.error_message
    assert first.rows_inserted == 32
    assert all(call.request.headers["X-API-Key"] == "fixture-token" for call in external_http.calls)
    second = source.execute("load", start="2019-01-01", end="2019-01-02")
    assert second.rows_inserted == 0


def test_http_retries_429_and_5xx_with_delay(external_http):
    delays = []
    external_http.get("https://example.test/rows", status=429, headers={"Retry-After": "2"})
    external_http.get("https://example.test/rows", status=503)
    external_http.get("https://example.test/rows", json={"ok": True})
    response = HttpClient(sleep=delays.append).get("https://example.test/rows")
    assert response.json() == {"ok": True}
    assert delays == [2, 2] and len(external_http.calls) == 3


def test_cache_checks_hash_and_rejects_path_escape(raw, external_http):
    body = (FIXTURES / "opencity-delhi.csv").read_bytes()
    external_http.get("https://example.test/rows.csv", body=body)
    path, manifest = raw.download("https://example.test/rows.csv", "samples/rows.csv")
    assert manifest["sha256"] == digest_file(path)
    raw.download("https://example.test/rows.csv", "samples/rows.csv")
    assert len(external_http.calls) == 1
    path.write_bytes(b"changed")
    with pytest.raises(ValueError, match="SHA256"):
        raw.local(path)
    with pytest.raises(ValueError, match="inside"):
        raw.path("../escape.csv")


def test_secret_redaction(monkeypatch):
    monkeypatch.setenv("FIRMS_MAP_KEY", "private-test-key")
    assert "private-test-key" not in safe_url("https://firms.test/private-test-key?api_key=secret")
    assert "secret" not in safe_url("https://firms.test/path?api_key=secret")


@pytest.mark.django_db
def test_lifecycle_partial_persists_and_failure_is_not_success(seeded, raw):
    source = Source(cache=raw)
    source.slug, source.name = "fixture", "Fixture"
    with source.lifecycle("tests.failure"):
        raise RuntimeError("download failed")
    assert source.run.status == IngestionRun.Status.FAILED
    with source.lifecycle("tests.partial"):
        source.run.rows_inserted = 1
        raise RuntimeError("second file failed")
    assert source.run.status == IngestionRun.Status.PARTIAL


@pytest.mark.django_db
def test_beat_schedules_are_editable_and_idempotent():
    from django_celery_beat.models import PeriodicTask

    configure_schedules()
    tasks = PeriodicTask.objects.filter(name__startswith="Phase 2")
    assert tasks.count() == 3
    item = tasks.get(task="ingest.openaq_hourly")
    item.enabled = False
    item.save()
    configure_schedules()
    item.refresh_from_db()
    assert not item.enabled and tasks.count() == 3


@pytest.mark.django_db
def test_actual_boundary_geometry_links_city_and_second_load_changes_nothing(
    seeded, raw, monkeypatch
):
    from apps.ingest.models import CityDistrictLink
    from apps.ingest.sources import boundaries
    from apps.warehouse.models import District, State

    source = BoundarySource(cache=raw)
    for kind in ["states", "districts"]:
        copy_fixture(raw, f"boundary-{kind}.geojson", f"boundaries/{kind}/sample.shp")
    monkeypatch.setattr(boundaries, "LAYERS", {"states": "sample", "districts": "sample"})
    City.objects.exclude(slug="delhi").delete()
    first = source.execute("load")
    assert first.status == "success", first.error_message
    assert District.objects.count() == 9 and CityDistrictLink.objects.count() == 1
    assert State.objects.get(code="DL").geometry.covers(City.objects.get(slug="delhi").location)
    assert source.execute("load").rows_inserted == 0


@pytest.mark.django_db
def test_real_boundary_state_aliases_preserve_census_identity_and_provenance(
    seeded, raw, monkeypatch
):
    import hashlib
    import re

    from apps.ingest.models import BoundaryProvenance
    from apps.ingest.sources import boundaries
    from apps.warehouse.models import District, State

    City.objects.all().delete()
    for label in ["Dadara & Nagar Havelli", "Daman & Diu"]:
        key = re.sub(r"[^a-z ]", "", label.lower()).strip()
        State.objects.create(name=label, code="B" + hashlib.sha256(key.encode()).hexdigest()[:8])
    for kind in ["states", "districts"]:
        copy_fixture(raw, f"boundary-alias-{kind}.geojson", f"boundaries/{kind}/sample.shp")
    monkeypatch.setattr(boundaries, "LAYERS", {"states": "sample", "districts": "sample"})
    source = BoundarySource(cache=raw)
    first = source.execute("load")
    assert first.status == "success", first.error_message
    assert set(District.objects.values_list("state__code", flat=True)) == {"AR", "AN", "DN", "DD"}
    assert District.objects.count() == 4
    assert not State.objects.filter(code__regex=r"^B[0-9a-f]{8}$").exists()
    parents = State.objects.filter(code__in=["AR", "AN", "DN", "DD", "DH"])
    assert BoundaryProvenance.objects.filter(state__in=parents).count() == 5
    assert State.objects.get(code="DN").geometry is None  # No invented historical polygon.
    assert source.execute("load").rows_inserted == 0
    assert District.objects.count() == 4


@pytest.mark.django_db
def test_cds_split_netcdf_contract_retains_all_real_era5_variables(seeded, raw):
    source = ERA5Source(cache=raw)
    path = copy_fixture(raw, "era5-contract.zip", "era5/delhi/sample.nc")
    city = City.objects.get(slug="delhi")
    for iteration in range(2):
        with source.lifecycle("tests.cds-nc"):
            source.load_netcdf(path, city)
        assert source.run.status == "success", source.run.error_message
        assert source.run.rows_inserted == (2 if iteration == 0 else 0)
    first = WeatherObservation.objects.order_by("observed_at").first()
    payload = json.loads((FIXTURES / "openmeteo.json").read_text())["hourly"]
    assert first.temperature_c == pytest.approx(payload["temperature_2m"][0])
    assert first.precipitation_mm == pytest.approx(payload["precipitation"][0])
    assert first.solar_radiation_wm2 == pytest.approx(payload["shortwave_radiation"][0])
    assert first.boundary_layer_height_m is None


@pytest.mark.django_db
def test_openmeteo_current_archive_supplies_real_boundary_layer_height(seeded, raw):
    source = OpenMeteoSource(cache=raw)
    path = copy_fixture(raw, "openmeteo-blh.json", "openmeteo/delhi/blh.json")
    with source.lifecycle("tests.real-blh"):
        _, asset = source.local_asset(path)
        source.load_payload(json.loads(path.read_text()), City.objects.get(slug="delhi"), asset)
    assert source.run.status == "success", source.run.error_message
    first = WeatherObservation.objects.order_by("observed_at").first()
    assert first.boundary_layer_height_m == 45
    assert first.temperature_c is None  # The source response contains only BLH.


def test_cache_preserves_previous_inputs_when_parameters_change(raw, external_http):
    url = "https://example.test/weather"
    external_http.get(url, json=json.loads((FIXTURES / "openmeteo.json").read_text()))
    first, manifest = raw.download(url, "weather.json", params={"hourly": "temperature_2m"})
    external_http.replace(
        responses.GET, url, json=json.loads((FIXTURES / "openmeteo-blh.json").read_text())
    )
    second, _ = raw.download(url, "weather.json", params={"hourly": "boundary_layer_height"})
    assert first != second and first.exists() and second.exists()
    assert digest_file(first) == manifest["sha256"]


def test_anonymous_ftp_resumes_verified_real_sample(raw, monkeypatch):
    from io import BytesIO

    from apps.ingest import http

    body = (FIXTURES / "cpcb-hourly.csv").read_bytes()

    class Probe(BytesIO):
        def recv(self, count):
            return self.read(count)

    class FTP:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def login(self):
            pass

        def voidcmd(self, command):
            pass

        def connect(self, host):
            pass

        def close(self):
            pass

        def size(self, path):
            return len(body)

        def sendcmd(self, command):
            return "213 20250719043011"

        def transfercmd(self, command, rest):
            return Probe(body[rest:])

        def retrbinary(self, command, callback, blocksize, rest):
            callback(body[rest or 0 :])

    monkeypatch.setattr(http.ftplib, "FTP", FTP)
    target = raw.path("cpcb/sample.csv")
    target.with_name(target.name + ".part").write_bytes(body[:100])
    path, manifest = raw.download_ftp("ftp://provider.test/sample.csv", "cpcb/sample.csv")
    assert path.read_bytes() == body
    assert manifest["resumed_bytes"] == 100 and manifest["sha256"] == digest_file(path)


def test_ftp_refuses_unverified_partial_bytes(raw, monkeypatch):
    from io import BytesIO

    from apps.ingest import http

    class Probe(BytesIO):
        def recv(self, size):
            return self.read(size)

    class FTP:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def login(self):
            pass

        def voidcmd(self, command):
            pass

        def size(self, path):
            return 100

        def sendcmd(self, command):
            return "213 20250719043011"

        def transfercmd(self, command, rest):
            return Probe(b"different")

    monkeypatch.setattr(http.ftplib, "FTP", FTP)
    target = raw.path("sample.csv")
    target.with_name(target.name + ".part").write_bytes(b"original")
    with pytest.raises(ValueError, match="differ"):
        raw.download_ftp("ftp://provider.test/sample.csv", "sample.csv")


@pytest.mark.django_db
def test_worldpop_real_raster_subset_registers_metadata_idempotently(seeded, raw):
    from apps.ingest.sources.worldpop import WorldPopSource

    source = WorldPopSource(cache=raw)
    copy_fixture(raw, "worldpop-delhi.tif", source.filename)
    first = source.execute("load")
    assert first.status == "success", first.error_message
    assert first.rows_inserted == 1
    asset = RawAsset.objects.get(pk=first.params["asset_id"])
    assert asset.metadata["width"] == asset.metadata["height"] == 8
    assert asset.metadata["srid"] == 4326 and asset.metadata["nodata"] == -99999
    assert source.execute("load").rows_inserted == 0


@pytest.mark.django_db
def test_opencity_broad_search_never_labels_another_citys_package(
    seeded, raw, monkeypatch, external_http
):
    source = OpenCitySource(cache=raw)
    City.objects.exclude(slug="ahmedabad").delete()
    external_http.get(
        "https://data.opencity.in/api/3/action/package_search",
        json={
            "success": True,
            "result": {
                "results": [
                    {
                        "name": "delhi-hourly-air-quality-reports",
                        "resources": [
                            {
                                "id": "wrong-city",
                                "name": "Delhi export",
                                "format": "CSV",
                                "url": "https://example.test/should-not-download.csv",
                            }
                        ],
                    }
                ]
            },
        },
    )
    monkeypatch.setattr(source, "registry", lambda: [])
    run = source.execute("download")
    assert run.status == "success" and run.params["catalogue_counts"]["ahmedabad"] == 0
    assert len(external_http.calls) == 1


@pytest.mark.django_db
def test_real_station_id_resolves_shared_station_name(seeded, raw):
    from apps.ingest.sources.air import AirSource

    registry = json.loads((FIXTURES / "station-identity-aliases.json").read_text())["data"]
    source = CPCBArchiveSource(cache=raw)
    info = next(x for x in registry if x["station_id"] == "site_107")
    with source.lifecycle("tests.station-identity"):
        station = AirSource.station(
            source,
            info["station_name"],
            info["station_id"],
            City.objects.get(slug="delhi"),
            registry=registry,
        )
    assert source.run.status == "success", source.run.error_message
    assert station.location.y == info["latitude"] and station.location.x == info["longitude"]


@pytest.mark.django_db
def test_real_coordinate_supplement_is_traceable_and_does_not_invent_points(
    seeded, raw, external_http
):
    from apps.ingest.sources.air import COORDINATE_SNAPSHOT

    external_http.get(
        REGISTRY_URL, json=json.loads((FIXTURES / "station-registry-missing.json").read_text())
    )
    external_http.get(
        COORDINATE_SNAPSHOT, body=(FIXTURES / "station-coordinate-supplement.csv").read_bytes()
    )
    source = CPCBArchiveSource(cache=raw)
    with source.lifecycle("tests.coordinate-supplement"):
        registry = source.registry()
        station = source.station(
            "Gandhi Nagar_Ennore, Chennai - TNPCB",
            "site_5618",
            City.objects.get(slug="chennai"),
            registry=registry,
        )
    assert source.run.status == "success", source.run.error_message
    assert station.location.y == 13.218341 and station.location.x == 80.32027
    assert source.run.params["coordinate_supplement_stations"]["site_5618"]["asset"]
    assert RawAsset.objects.count() == 2
