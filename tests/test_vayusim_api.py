from datetime import UTC, datetime
from unittest.mock import patch

import numpy as np
import pytest
import rasterio
from affine import Affine
from django.contrib.gis.geos import Point
from pyproj import CRS

from apps.rag.data_tools import call_tool
from apps.vayusim.exposure import exposure_summary, population_grid
from apps.vayusim.grid import build_grid
from apps.vayusim.models import ScenarioRun
from apps.vayusim.weather import hour_bounds, weather_for
from tests.factories import CityFactory, DataSourceFactory


@pytest.fixture
def inputs(db):
    city = CityFactory(slug="delhi", location=Point(77.2, 28.6, srid=4326))
    return {
        "name": "Synthetic test only",
        "city": city.slug,
        "centre": [77.2, 28.6],
        "sources": [
            {
                "type": "point",
                "location": [77.2, 28.6],
                "emission_gs": 10.0,
                "height_m": 50.0,
                "diameter_m": 2.0,
                "exit_velocity_ms": 10.0,
                "exit_temperature_k": 400.0,
            }
        ],
        "weather_mode": "manual",
        "datetime": "2025-01-01T12:00:00+05:30",
        "weather": {
            "wind_speed_ms": 4.0,
            "wind_direction_deg": 270.0,
            "temperature_k": 293.0,
            "solar_radiation_wm2": 500.0,
            "cloud_fraction": 0.2,
            "mixing_height_m": 1000.0,
            "daytime": True,
        },
        "grid": {"width_m": 1000, "resolution_m": 50},
        "thresholds": [10.0],
    }


@pytest.mark.django_db
def test_identical_api_requests_cache_grid_and_provenance(client, inputs, tmp_path, settings):
    settings.BASE_DIR = tmp_path
    first = client.post("/api/vayusim/run/", inputs, content_type="application/json")
    assert first.status_code == 200, first.content
    value = first.json()
    second = client.post(
        "/api/vayusim/run/",
        {**inputs, "name": "Different presentation name"},
        content_type="application/json",
    )
    assert second.status_code == 200
    assert second.json()["cached"] and second.json()["run_id"] == value["run_id"]
    assert ScenarioRun.objects.count() == 1
    header = client.get(value["grid_header_url"]).json()
    assert header["shape"] == [20, 20] and header["dtype"] == "float32"
    binary = client.get(value["grid_url"])
    assert len(b"".join(binary.streaming_content)) == 20 * 20 * 4
    assert client.get(value["overlay_url"]).content[:8] == b"\x89PNG\r\n\x1a\n"
    assert client.get("/api/vayusim/scenarios/" + value["scenario_slug"] + "/").status_code == 200
    evidence = call_tool("vayusim_run", {"run_id": value["run_id"]})
    assert evidence["values"]["peak_ugm3"] == value["summary"]["peak_ugm3"]
    assert evidence["citation"]["inputs_hash"] == value["inputs_hash"]
    assert evidence["citation"]["scenario_run"] == value["run_id"]
    assert evidence["values"]["label"] == "modelled increment from these sources only"
    assert not value["summary"]["exposure"]["available"]


@pytest.mark.django_db
@pytest.mark.parametrize(
    "mutation",
    [
        {"city": "unknown"},
        {"sources": [{"emission_gs": -1}]},
        {"receptor_height": 1001},
        {"receptor_height": "NaN"},
        {"centre": [float("inf"), 28.0]},
        {"unknown": 1},
    ],
)
def test_api_rejects_invalid_input(client, inputs, mutation):
    payload = {**inputs, **mutation}
    if "sources" in mutation:
        # Isolate the invalid value; all other required source fields stay valid.
        payload["sources"] = [{**inputs["sources"][0], **mutation["sources"][0]}]
    assert (
        client.post("/api/vayusim/run/", payload, content_type="application/json").status_code
        == 400
    )
    assert ScenarioRun.objects.count() == 0


def test_hour_midpoint_accounts_for_ist_half_hour():
    start, end = hour_bounds(datetime.fromisoformat("2025-01-01T12:00:00+05:30"))
    assert start == datetime(2025, 1, 1, 6, 30, tzinfo=UTC)
    assert start + (end - start) / 2 == datetime(2025, 1, 1, 7, tzinfo=UTC)


@pytest.mark.django_db
def test_real_weather_utc_midpoint_and_fallback(inputs):
    from apps.warehouse.models import City, WeatherObservation

    city = City.objects.get(slug="delhi")
    weather = WeatherObservation.objects.create(
        city=city,
        source=DataSourceFactory(),
        location=city.location,
        observed_at=datetime(2025, 1, 1, 7, tzinfo=UTC),
        wind_speed_ms=4,
        wind_dir_deg=270,
        temperature_c=20,
        solar_radiation_wm2=400,
        total_cloud_cover=0.2,
        boundary_layer_height_m=None,
    )
    values, proof, flags = weather_for(
        {**inputs, "weather_mode": "real", "datetime": datetime.fromisoformat(inputs["datetime"])},
        city,
    )
    assert proof["observation_id"] == str(weather.id)
    assert values["stability_class"] == "C" and values["temperature_k"] == pytest.approx(293.15)
    assert not proof["mixing_height"]["observed"] and proof["mixing_height"]["citations"]
    assert any("Missing boundary-layer" in f for f in flags)


def test_exposure_density_warp_preserves_known_counts(tmp_path):
    # Same projected source/destination extent,100m cells split into50m cells.
    path = tmp_path / "population.tif"
    crs = CRS.from_epsg(32643)
    transform = Affine(100, 0, 500000, 0, -100, 3200000)
    counts = np.array([[100.0, 200.0], [300.0, 400.0]], dtype="float32")
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=2,
        width=2,
        count=1,
        dtype="float32",
        crs=crs,
        transform=transform,
        nodata=-9999,
    ) as dst:
        dst.write(counts, 1)
    from pyproj import Transformer

    inverse = Transformer.from_crs(crs, 4326, always_xy=True)
    grid = {
        "crs": crs,
        "affine": Affine(50, 0, 500000, 0, -50, 3200000),
        "corners": [inverse.transform(*(transform @ p)) for p in [(0, 0), (2, 0), (2, 2), (0, 2)]],
    }
    population = population_grid(path, grid, (4, 4))
    np.testing.assert_allclose(population.sum(), 1000.0, rtol=1e-6)
    np.testing.assert_allclose(population[:2, :2], 25.0)
    field = np.zeros((4, 4))
    field[:2, :2] = 20.0
    summary = exposure_summary(field, population, [1.0, 15.0, 60.0])
    assert summary["population_above"]["15.0"] == pytest.approx(100.0)
    assert summary["population_weighted_mean_added_ugm3"] == pytest.approx(2.0)
    # Four100m destination cells recover the source counts.
    grid["affine"] = transform
    np.testing.assert_allclose(population_grid(path, grid, (2, 2)), counts, rtol=1e-6)


def test_rotated_grid_geometry():
    grid = build_grid([77.2, 28.6], 270.0, 1000, 50)
    assert grid["east"].shape == (20, 20)
    assert grid["east"][0, 1] - grid["east"][0, 0] == pytest.approx(50.0)
    assert grid["north"][1, 0] - grid["north"][0, 0] == pytest.approx(-50.0)
    assert abs(grid["affine"].determinant) == pytest.approx(2500.0)


def test_partial_population_nodata_does_not_inflate_known_counts(tmp_path):
    from pyproj import Transformer

    path = tmp_path / "partial-population.tif"
    crs = CRS.from_epsg(32643)
    transform = Affine(100, 0, 500000, 0, -100, 3200000)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=2,
        width=2,
        count=1,
        dtype="float32",
        crs=crs,
        transform=transform,
        nodata=-9999,
    ) as dst:
        dst.write(np.array([[100.0, -9999.0], [300.0, -9999.0]], dtype="float32"), 1)
    inverse = Transformer.from_crs(crs, 4326, always_xy=True)
    grid = {
        "crs": crs,
        "affine": Affine(200, 0, 500000, 0, -200, 3200000),
        "corners": [inverse.transform(*(transform @ p)) for p in [(0, 0), (2, 0), (2, 2), (0, 2)]],
    }
    population, support = population_grid(path, grid, (1, 1), return_support=True)
    assert population[0, 0] == pytest.approx(400.0)
    assert support[0, 0] == pytest.approx(0.5)
    summary = exposure_summary(np.array([[20.0]]), population, [1.0], support)
    assert summary["population_above"]["1.0"] == pytest.approx(400.0)
    assert summary["population_support_fraction"] == pytest.approx(0.5)
    assert summary["partially_supported_cells"] == 1


@pytest.mark.django_db
def test_explain_uses_server_run_context(client, inputs, tmp_path, settings):
    settings.BASE_DIR = tmp_path
    response = client.post("/api/vayusim/run/", inputs, content_type="application/json").json()
    with patch("apps.rag.api.ask", return_value={"answer": "test evidence"}) as ask:
        result = client.post(
            "/api/rag/explain/",
            {
                "context_type": "scenario",
                "payload": {"run_id": response["run_id"], "parameters": {"peak": 999999}},
            },
            content_type="application/json",
        )
    assert result.status_code == 200
    assert ask.call_args.kwargs["context_tool_calls"] == [
        {"tool": "vayusim_run", "parameters": {"run_id": response["run_id"]}}
    ]


@pytest.mark.django_db
@pytest.mark.parametrize("parameters", [{"run_id": True}, {"run_id": 1, "peak": 99}])
def test_scenario_tool_rejects_bool_and_client_values(parameters):
    from rest_framework.exceptions import ValidationError

    with pytest.raises(ValidationError):
        call_tool("vayusim_run", parameters)


@pytest.mark.django_db
def test_day_mode_keeps_missing_hours_and_materialises_grid_on_demand(
    client, inputs, tmp_path, settings
):
    from apps.warehouse.models import City, WeatherObservation

    settings.BASE_DIR = tmp_path
    city = City.objects.get(slug="delhi")
    WeatherObservation.objects.create(
        city=city,
        source=DataSourceFactory(),
        location=city.location,
        observed_at=datetime(2025, 1, 1, 7, tzinfo=UTC),
        wind_speed_ms=4,
        wind_dir_deg=270,
        temperature_c=20,
        solar_radiation_wm2=400,
        total_cloud_cover=0.2,
        boundary_layer_height_m=1000,
    )
    payload = {k: v for k, v in inputs.items() if k != "weather"}
    payload["weather_mode"] = "real"
    response = client.post("/api/vayusim/day/", payload, content_type="application/json")
    assert response.status_code == 200, response.content
    hours = response.json()["hours"]
    assert len(hours) == 24 and sum(h["available"] for h in hours) == 1
    hour = next(h for h in hours if h["available"])
    run = ScenarioRun.objects.get(pk=hour["run_id"])
    assert run.grid_file_path == "" and run.summary["contours"] is None
    header = client.get(hour["grid_header_url"])
    assert header.status_code == 200 and header.json()["contours"]["type"] == "FeatureCollection"
    run.refresh_from_db()
    assert run.grid_file_path and ScenarioRun.objects.count() == 1


@pytest.mark.django_db(transaction=True)
def test_concurrent_lazy_grid_requests_compute_once(inputs, tmp_path, settings):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from django.db import close_old_connections, connections
    from django.db.migrations.executor import MigrationExecutor

    from apps.vayusim import service
    from apps.vayusim.serializers import RunSerializer

    settings.BASE_DIR = tmp_path
    # The original foundation reversal test restores warehouse only, so later
    # transactional tests must explicitly arrange a fully migrated schema.
    # Keep that test and every concurrency assertion unchanged.
    executor = MigrationExecutor(connections["default"])
    executor.migrate(executor.loader.graph.leaf_nodes())
    serializer = RunSerializer(data=inputs)
    serializer.is_valid(raise_exception=True)
    run, _ = service.run_scenario(serializer.validated_data, materialize=False)
    barrier = Barrier(2)

    def materialise(_):
        close_old_connections()
        try:
            instance = ScenarioRun.objects.get(pk=run.pk)
            barrier.wait(timeout=10)
            service.ensure_grid(instance)
            return instance.grid_file_path
        finally:
            connections.close_all()

    with patch("apps.vayusim.service.compute", wraps=service.compute) as compute:
        with ThreadPoolExecutor(max_workers=2) as pool:
            paths = list(pool.map(materialise, range(2)))
    assert paths[0] == paths[1] and paths[0]
    assert compute.call_count == 1 and ScenarioRun.objects.count() == 1


@pytest.mark.django_db
def test_old_lazy_run_never_recomputes_under_new_engine(client, inputs, tmp_path, settings):
    from apps.vayusim import service
    from apps.vayusim.serializers import RunSerializer

    settings.BASE_DIR = tmp_path
    serializer = RunSerializer(data=inputs)
    serializer.is_valid(raise_exception=True)
    run, _ = service.run_scenario(serializer.validated_data, materialize=False)
    original_summary = run.summary
    run.engine_version = "historical-engine"
    run.save(update_fields=["engine_version"])
    with patch("apps.vayusim.service.compute") as compute:
        response = client.get(f"/api/vayusim/grid/{run.pk}.json")
    assert response.status_code == 400 and "saved inputs" in response.json()["grid"]
    compute.assert_not_called()
    run.refresh_from_db()
    assert run.summary == original_summary and not run.grid_file_path
    assert (
        client.get(f"/api/vayusim/runs/{run.pk}/").json()["engine_version"] == "historical-engine"
    )


@pytest.mark.django_db
def test_lazy_grid_uses_frozen_run_after_scenario_edit(inputs, tmp_path, settings):
    from apps.vayusim import service
    from apps.vayusim.serializers import RunSerializer

    settings.BASE_DIR = tmp_path
    serializer = RunSerializer(data=inputs)
    serializer.is_valid(raise_exception=True)
    run, _ = service.run_scenario(serializer.validated_data, materialize=False)
    original_peak = run.summary["peak_ugm3"]
    original_hash = run.inputs_hash
    run.scenario.inputs["sources"][0]["emission_gs"] *= 100
    run.scenario.save(update_fields=["inputs"])
    service.ensure_grid(run)
    values = np.fromfile(tmp_path / run.grid_file_path, dtype="<f4")
    assert float(values.max()) == original_peak and original_peak > 0
    run.refresh_from_db()
    assert run.inputs_hash == original_hash
    assert run.inputs["sources"][0]["emission_gs"] == inputs["sources"][0]["emission_gs"]
