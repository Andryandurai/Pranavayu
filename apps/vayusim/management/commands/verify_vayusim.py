"""Reproduce the report's explicitly hypothetical sources using real archived data."""

import json
import time
from pathlib import Path

import numpy as np
from django.conf import settings
from django.core.management.base import BaseCommand

from apps.vayusim.grid import build_grid, project_sources
from apps.vayusim.physics import simulate
from apps.vayusim.serializers import RunSerializer
from apps.vayusim.service import run_response, run_scenario
from apps.warehouse.models import City


class Command(BaseCommand):
    help = "Verify three real-weather/WorldPop scenarios and benchmark the NumPy engine."

    def add_arguments(self, parser):
        parser.add_argument("--output", default="data/results/vayusim/verification")

    def handle(self, **options):
        folder = Path(settings.BASE_DIR) / options["output"]
        folder.mkdir(parents=True, exist_ok=True)
        examples = [
            ("delhi", "2025-01-15T12:00:00+05:30"),
            ("mumbai", "2025-07-15T15:00:00+05:30"),
            ("hyderabad", "2025-11-15T20:00:00+05:30"),
        ]
        results = []
        for slug, moment in examples:
            city = City.objects.get(slug=slug)
            centre = [city.location.x, city.location.y]
            source = {
                "type": "point",
                "location": centre,
                "emission_gs": 1.0,
                "height_m": 50.0,
                "diameter_m": 0.0,
                "exit_velocity_ms": 0.0,
                "exit_temperature_k": 293.15,
                "assumptions": (
                    "Declared hypothetical1g/s primary PM2.5 release at50m; no plume rise. "
                    "Not a measured facility or preset default. Temperature arbitrary for "
                    "zero-flow source and has no rise effect."
                ),
            }
            data = {
                "name": "Phase6A explicit unit-release demonstration " + slug,
                "city": slug,
                "centre": centre,
                "sources": [source],
                "weather_mode": "real",
                "datetime": moment,
                "thresholds": [5.0],
            }
            serializer = RunSerializer(data=data)
            serializer.is_valid(raise_exception=True)
            run, cached = run_scenario(serializer.validated_data)
            results.append(run_response(run, cached))
            self.stdout.write(
                json.dumps({"city": slug, "run_id": run.pk, "peak_ugm3": run.summary["peak_ugm3"]})
            )
        (folder / "real-scenarios.json").write_text(
            json.dumps(results, indent=2, ensure_ascii=False)
        )
        # Explicit software-benchmark inputs, not a facility preset or measured inventory.
        source = {
            "type": "point",
            "location": [77.2, 28.6],
            "emission_gs": 1.0,
            "height_m": 50.0,
            "diameter_m": 2.0,
            "exit_velocity_ms": 10.0,
            "exit_temperature_k": 400.0,
        }
        weather = {
            "wind_speed_ms": 4.0,
            "wind_direction_deg": 270.0,
            "temperature_k": 293.15,
            "stability_class": "D",
            "mixing_height_m": 1000.0,
        }
        grid = build_grid([77.2, 28.6], 270.0)
        projected = project_sources([source], grid)
        benchmarks = {}
        for count in [1, 20]:
            times = []
            for repetition in range(21):
                started = time.perf_counter()
                simulate(grid["east"], grid["north"], projected * count, weather)
                elapsed = (time.perf_counter() - started) * 1000
                if repetition:
                    times.append(elapsed)
            benchmarks[str(count)] = {
                "median_ms": float(np.median(times)),
                "min_ms": min(times),
                "max_ms": max(times),
                "repeats": 20,
            }
        benchmarks["conditions"] = (
            "200x200 float32 output; NumPy1 thread; other Docker services active; engine only; "
            "projection, population and artifacts excluded. Record concurrent CPU jobs separately."
        )
        (folder / "benchmarks.json").write_text(json.dumps(benchmarks, indent=2))
        self.stdout.write(json.dumps(benchmarks))
