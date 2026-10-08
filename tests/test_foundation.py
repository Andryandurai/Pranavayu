from unittest.mock import MagicMock, patch

import pytest
from django.apps import apps
from django.contrib import admin
from django.db import models
from django.urls import resolve
from rest_framework.test import APIRequestFactory

from apps.core.admin_site import EnviroAdminSite, ReadOnlyCompositeAdmin
from apps.core.health import infrastructure_health
from apps.core.views import HealthView
from apps.rag.models import DocumentChunk
from apps.warehouse.models import City, FireDetection, Reading, Station, WeatherObservation
from apps.warehouse.pagination import BoundedGeoJsonPagination
from apps.warehouse.reference import CITIES, POLLUTANTS, SOURCES
from apps.warehouse.serializers import StationSerializer


@pytest.mark.parametrize(
    "model,fields",
    [
        (Reading, ("station_id", "pollutant_id", "observed_at")),
        (WeatherObservation, ("id", "observed_at")),
        (FireDetection, ("id", "detected_at")),
    ],
)
def test_composite_keys_include_time_without_scalar_primary_key(model, fields):
    assert isinstance(model._meta.pk, models.CompositePrimaryKey)
    assert model._meta.pk.field_names == fields
    assert not any(field.primary_key for field in model._meta.local_fields if field.concrete)
    assert all(field.name not in {"created_at", "updated_at"} for field in model._meta.fields)


def test_every_project_model_has_an_admin():
    for app in ("warehouse", "ingest", "rag"):
        for model in apps.get_app_config(app).get_models():
            assert admin.site.is_registered(model), model.__name__


@pytest.mark.parametrize("model", [Reading, WeatherObservation, FireDetection])
def test_composite_admin_exposes_only_changelist_routes(model):
    listing = admin.site.get_model_admin(model)
    assert isinstance(listing, ReadOnlyCompositeAdmin)
    assert [str(url.pattern) for url in listing.get_urls()] == [""]
    assert listing.actions is None
    assert listing.list_display_links is None
    assert not listing.show_full_result_count
    assert not listing.has_change_permission(None)


def test_composite_admin_rejects_editable_registration():
    with pytest.raises(ValueError, match="read-only"):
        EnviroAdminSite().register(Reading, admin.ModelAdmin)


def test_station_serializer_outputs_a_geojson_feature_without_database():
    from django.contrib.gis.geos import Point

    station = Station(
        id=1,
        external_id="unit-test",
        source_id=1,
        name="Test station",
        location=Point(77.2, 28.6, srid=4326),
        city_id=None,
    )
    data = StationSerializer(station).data
    assert data["type"] == "Feature"
    assert data["geometry"]["type"] == "Point"
    assert data["geometry"]["coordinates"] == [77.2, 28.6]
    assert BoundedGeoJsonPagination.max_page_size == 100


def test_document_chunk_dimension_and_index_definitions():
    assert DocumentChunk._meta.get_field("embedding").dimensions == 1024
    indexes = {index.name: index for index in DocumentChunk._meta.indexes}
    assert indexes["chunk_embedding_hnsw"].opclasses == ["vector_cosine_ops"]
    assert indexes["chunk_text_fts_gin"].expressions[0].config is not None


def test_reference_data_preserves_published_periods_and_missing_standards():
    pollutants = {entry[0]: entry for entry in POLLUTANTS}
    assert pollutants["pm25"][3:] == (15, 24, 60)
    assert pollutants["o3"][3:] == (100, 8, None)
    assert pollutants["co"][2:] == ("mg/m³", 4, 24, None)
    assert pollutants["nh3"][3:] == (None, None, 400)
    assert len(SOURCES) == len({entry[1] for entry in SOURCES}) == 12
    assert len(CITIES) == 12
    assert len({entry[2] for entry in CITIES}) == 10
    assert City._meta.get_field("population").null


def test_health_unit_reports_success_with_mocked_dependencies():
    # Explicit unit test; live services are checked separately in test_api.py.
    cursor = MagicMock()
    cursor.fetchone.return_value = (1,)
    cursor.fetchall.return_value = [
        ("postgis", "test"),
        ("timescaledb", "test"),
        ("vector", "test"),
    ]
    with (
        patch("apps.core.health.connection") as db,
        patch("apps.core.health.Redis") as redis,
        patch("apps.core.health.app") as celery,
    ):
        db.cursor.return_value.__enter__.return_value = cursor
        redis.from_url.return_value.__enter__.return_value.ping.return_value = True
        celery.control.inspect.return_value.ping.return_value = {"test": {"ok": "pong"}}
        assert infrastructure_health()["ok"]


def test_health_unit_detects_failures_without_leaking_errors():
    with (
        patch("apps.core.health.connection") as db,
        patch("apps.core.health.Redis") as redis,
        patch("apps.core.health.app") as celery,
    ):
        db.cursor.side_effect = RuntimeError("private connection information")
        redis.from_url.side_effect = RuntimeError("private connection information")
        celery.control.inspect.return_value.ping.return_value = None
        report = infrastructure_health()
    assert not report["ok"]
    assert not report["checks"]["database"]["ok"]
    assert not report["checks"]["redis"]["ok"]
    assert not report["checks"]["celery"]["ok"]
    assert "private" not in str(report)


def test_health_endpoint_returns_503_when_services_are_unhealthy():
    with patch("apps.core.views.infrastructure_health", return_value={"ok": False, "checks": {}}):
        response = HealthView.as_view()(APIRequestFactory().get("/api/health/"))
    assert response.status_code == 503


@pytest.mark.parametrize(
    "url", ["/", "/api/health/", "/api/schema/", "/api/docs/", "/api/stations/"]
)
def test_phase1_urls_resolve(url):
    assert resolve(url)


def test_extension_migrations_precede_spatial_and_vector_tables():
    # Build a graph without touching PostgreSQL; complements the real migration test.
    from django.db.migrations.loader import MigrationLoader

    loader = MigrationLoader(None)
    for app in ("warehouse", "rag"):
        plan = loader.graph.forwards_plan((app, "0001_initial"))
        assert plan.index(("core", "0001_extensions")) < plan.index((app, "0001_initial"))


def test_openapi_describes_actual_geojson_pagination():
    from drf_spectacular.drainage import GENERATOR_STATS
    from drf_spectacular.generators import SchemaGenerator

    GENERATOR_STATS.reset()
    schema = SchemaGenerator().get_schema(request=None, public=True)
    assert not GENERATOR_STATS
    for model in ("City", "Station"):
        page = schema["components"]["schemas"][f"Paginated{model}List"]
        assert page["properties"]["features"] == {
            "type": "array",
            "items": {"$ref": f"#/components/schemas/{model}"},
        }
        assert "features" in page["required"]
        assert "results" not in page["required"]
        assert "type" in page["required"]
