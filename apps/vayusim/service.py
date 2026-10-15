import hashlib
import json
import time
from pathlib import Path

import numpy as np
from django.conf import settings
from django.contrib.gis.geos import Point
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.analytics.models import PopulationRaster
from apps.warehouse.models import City

from .artifacts import contours
from .exposure import exposure_summary, population_grid
from .grid import build_grid, project_sources
from .models import Scenario, ScenarioRun
from .physics import ENGINE_VERSION, simulate
from .weather import background_stations, hour_bounds, weather_for

LIMITS = [
    "Primary PM2.5 only; no secondary formation, chemistry or deposition",
    "Flat terrain; no building downwash beyond stack-tip adjustment",
    "Steady state within the hour; uniform city-grid meteorology",
    "Educational estimate, not a regulatory assessment; use AERMOD for regulatory modelling",
    "Hourly added exposure; not24-hour/annual exposure or actual CPCB AQI",
]


def json_values(value):
    return json.loads(json.dumps(value, cls=DjangoJSONEncoder, allow_nan=False))


def compute(inputs, weather):
    grid = build_grid(inputs["centre"], weather["wind_direction_deg"], **inputs["grid"])
    sources = project_sources(inputs["sources"], grid)
    if any(np.hypot(s["east_m"], s["north_m"]) > 15000 for s in sources):
        raise ValidationError({"sources": "Sources must be within15km of the scenario centre"})
    if any(
        s["type"] == "line" and np.hypot(s["end_east_m"], s["end_north_m"]) > 15000 for s in sources
    ):
        raise ValidationError({"sources": "Line endpoints must be within15km of the centre"})
    values, flags = simulate(
        grid["east"],
        grid["north"],
        sources,
        weather,
        inputs["receptor_height"],
        inputs["environment"],
    )
    return values, grid, sources, flags


def run_scenario(inputs, materialize=True):
    started = time.perf_counter()
    inputs = {**inputs, "grid": {"width_m": 10000, "resolution_m": 50, **inputs.get("grid", {})}}
    city = City.objects.get(slug=inputs["city"])
    weather, provenance, flags = weather_for(inputs, city)
    population = (
        PopulationRaster.objects.filter(year=2025, is_default=True).select_related("asset").first()
    )
    canonical = json_values({k: v for k, v in inputs.items() if k != "name"})
    canonical["datetime"] = hour_bounds(inputs["datetime"])[0].isoformat()
    canonical.update(
        weather_values=weather,
        weather_provenance=provenance,
        population_sha256=population.asset.sha256 if population else None,
        engine_version=ENGINE_VERSION,
    )
    digest = hashlib.sha256(
        json.dumps(canonical, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()
    with transaction.atomic():
        # PostgreSQL transaction advisory lock serialises identical requests without
        # holding other scenarios. Unique hash is a second database-level safeguard.
        from django.db import connection

        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(%s)", [int(digest[:15], 16)])
        existing = ScenarioRun.objects.filter(inputs_hash=digest).select_related("scenario").first()
        if existing:
            if materialize:
                ensure_grid(existing)
            return existing, True
        values, grid, sources, engine_flags = compute(inputs, weather)
        flags += engine_flags
        thresholds = sorted(set([1.0, 15.0, 60.0, 120.0, *inputs["thresholds"]]))
        index = np.unravel_index(int(values.argmax()), values.shape)
        east, north = grid["east"][index], grid["north"][index]
        lon, lat = grid["inverse"].transform(east, north)
        exposure = {
            "label": "hourly added exposure",
            "available": False,
            "reason": "No registered WorldPop2025 raster",
        }
        population_provenance = None
        if population:
            path = Path(population.asset.path)
            if not path.is_absolute():
                path = Path(settings.BASE_DIR) / "data/raw" / path
            if path.exists():
                counts, support = population_grid(path, grid, values.shape, return_support=True)
                exposure = {
                    "available": True,
                    **exposure_summary(values, counts, thresholds, support),
                }
                population_provenance = {
                    "asset_id": population.asset_id,
                    "year": 2025,
                    "sha256": population.asset.sha256,
                    "url": population.asset.download_url,
                    "rationale": population.rationale,
                }
                if exposure["missing_population_cells"] or exposure["partially_supported_cells"]:
                    flags.append(
                        "Population nodata cells excluded; exposure covers supported cells only"
                    )
            else:
                exposure["reason"] = "Registered population file unavailable"
        if not exposure["available"]:
            flags.append("Population exposure unavailable; no zero substituted")
        summary = {
            "label": "modelled increment from these sources only",
            "unit": "µg/m³",
            "peak_ugm3": float(values[index]),
            "peak_location": [lon, lat],
            "distance_to_peak_m": min(
                float(np.hypot(east - s["east_m"], north - s["north_m"])) for s in sources
            ),
            "distance_definition": "Nearest discretised source to peak receptor",
            "area_above_km2": {
                str(t): float(np.sum(values > t) * abs(grid["affine"].determinant) / 1e6)
                for t in thresholds
            },
            "exposure": exposure,
            "weather": weather,
            "weather_provenance": provenance,
            "population_provenance": population_provenance,
            "source_assumptions": inputs["sources"],
            "background": background_stations(city, inputs["datetime"], inputs["centre"]),
            "limitations": LIMITS,
            "grid": {
                "shape": list(values.shape),
                "dtype": "float32",
                "byte_order": "little",
                "affine": list(grid["affine"])[:6],
                "crs": grid["crs"].to_wkt(),
                "corners": grid["corners"],
                "receptor_height_m": inputs["receptor_height"],
                "png_label": (
                    "CPCB category colours for visualisation only; hourly increment is not AQI"
                ),
            },
            "contours": contours(values, grid, thresholds) if materialize else None,
            "thresholds": thresholds,
        }
        scenario = Scenario.objects.create(
            name=inputs["name"],
            city=city,
            centre=Point(*inputs["centre"], srid=4326),
            sources=inputs["sources"],
            weather_mode=inputs["weather_mode"],
            date_hour=inputs["datetime"],
            receptor_height=inputs["receptor_height"],
            grid_settings=inputs["grid"],
            inputs=json_values(inputs),
        )
        run = ScenarioRun.objects.create(
            scenario=scenario,
            inputs_hash=digest,
            stability_class=weather["stability_class"],
            flags=sorted(set(flags)),
            summary=json_values(summary),
            inputs=canonical,
            engine_version=ENGINE_VERSION,
            run_time_ms=(time.perf_counter() - started) * 1000,
        )
        if materialize:
            store_grid(run, values)
        return run, False


def store_grid(run, values):
    folder = Path(settings.BASE_DIR) / "data/results/vayusim" / str(run.pk)
    folder.mkdir(parents=True, exist_ok=True)
    temporary = folder / "grid.bin.tmp"
    values.astype("<f4").tofile(temporary)
    path = folder / "grid.bin"
    temporary.replace(path)
    run.grid_file_path = str(path.relative_to(settings.BASE_DIR))
    run.save(update_fields=["grid_file_path"])


def ensure_grid(run):
    if run.grid_file_path and (Path(settings.BASE_DIR) / run.grid_file_path).exists():
        return
    if run.engine_version != ENGINE_VERSION:
        raise ValidationError(
            {
                "grid": (
                    "This run has no retained grid from its engine version. "
                    "Submit its saved inputs to create a current-version run; "
                    "the old summary is preserved."
                )
            }
        )
    with transaction.atomic():
        from django.db import connection

        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(%s)", [int(run.inputs_hash[:15], 16)])
        run.refresh_from_db(fields=["grid_file_path", "summary"])
        if run.grid_file_path and (Path(settings.BASE_DIR) / run.grid_file_path).exists():
            return
        materialize_grid(run)


def materialize_grid(run):
    # A Scenario can later be edited; a run's hashed snapshot remains its input.
    inputs = dict(run.inputs)
    values, grid, _, _ = compute(inputs, inputs["weather_values"])
    run.summary["contours"] = contours(values, grid, run.summary["thresholds"])
    run.save(update_fields=["summary"])
    store_grid(run, values)


def run_response(run, cached=False):
    prefix = f"/api/vayusim/grid/{run.pk}"
    return {
        "run_id": run.pk,
        "scenario_slug": run.scenario.share_slug,
        "cached": cached,
        "inputs_hash": run.inputs_hash,
        "engine_version": run.engine_version,
        "stability_class": run.stability_class,
        "flags": run.flags,
        "runtime_ms": run.run_time_ms,
        "summary": {k: v for k, v in run.summary.items() if k != "contours"},
        "contours": run.summary.get("contours"),
        "grid_url": prefix + ".bin",
        "grid_header_url": prefix + ".json",
        "overlay_url": prefix + ".png",
        "limitations": run.summary["limitations"],
    }
