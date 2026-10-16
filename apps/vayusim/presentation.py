"""Stored supplementary artifacts; no alternative physics or fitted parameters."""

import io
import json
from pathlib import Path

import numpy as np
from django.conf import settings
from django.db import connection, transaction
from PIL import Image, ImageDraw, PngImagePlugin
from rest_framework.exceptions import ValidationError

from .artifacts import overlay_png
from .grid import build_grid, project_sources
from .physics import ENGINE_VERSION, simulate
from .service import ensure_grid, validation_status


def section_path(run):
    return Path(settings.BASE_DIR) / "data/results/vayusim" / str(run.pk) / "section-v1.json"


def store_section(run):
    path = section_path(run)
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(%s)", [int(run.inputs_hash[:15], 16)])
        if path.exists():
            return
        if run.engine_version != ENGINE_VERSION:
            raise ValidationError("No retained vertical grid for this historical engine version")
        inputs = run.inputs
        weather = inputs["weather_values"]
        grid = build_grid(inputs["centre"], weather["wind_direction_deg"], **inputs["grid"])
        sources = project_sources(inputs["sources"], grid)
        distances = np.arange(0, inputs["grid"]["width_m"] / 2 + 1, inputs["grid"]["resolution_m"])
        heights = np.linspace(0, max(1000, max(s["height_m"] for s in sources) * 2), 61)
        theta = np.deg2rad((weather["wind_direction_deg"] + 180) % 360)
        east = sources[0]["east_m"] + distances * np.sin(theta)
        north = sources[0]["north_m"] + distances * np.cos(theta)
        values = [
            simulate(east, north, sources, weather, float(z), inputs["environment"])[0].tolist()
            for z in heights
        ]
        body = {
            "run_id": run.pk,
            "inputs_hash": run.inputs_hash,
            "engine_version": run.engine_version,
            "validation_status": validation_status(run),
            "label": "Vertical cross-section from stored grid data only",
            "method": (
                "Supplementary grid from retained inputs; unchanged engine; "
                "not inferred from the single-height horizontal grid"
            ),
            "origin": inputs["sources"][0]["location"],
            "direction_from_deg": weather["wind_direction_deg"],
            "distance_m": distances.tolist(),
            "height_m": heights.tolist(),
            "values_ugm3": values,
            "limitations": run.summary["limitations"],
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(body, allow_nan=False), encoding="utf-8")
        temporary.replace(path)


def export_png(run):
    ensure_grid(run)
    path = Path(settings.BASE_DIR) / run.grid_file_path
    values = np.fromfile(path, dtype="<f4").reshape(run.summary["grid"]["shape"])
    overlay = Image.open(io.BytesIO(overlay_png(values))).convert("RGBA")
    canvas = Image.new("RGB", (900, 980), "#101e26")
    canvas.paste(
        overlay.resize((560, 560), Image.Resampling.NEAREST),
        (170, 112),
        overlay.resize((560, 560), Image.Resampling.NEAREST),
    )
    draw = ImageDraw.Draw(canvas)
    status = validation_status(run).replace("_", " ")
    lines = [
        ("VayuSim | " + run.scenario.city.name + " | stored run " + str(run.pk), "white"),
        (
            status.upper()
            + " | "
            + run.inputs.get("environment", "urban")
            + " Briggs "
            + run.stability_class,
            "#ffc267",
        ),
        ("modelled increment from these sources only", "#d0e3db"),
        (
            "Peak: "
            + format(run.summary["peak_ugm3"], ".6g")
            + " ug/m3 | distance: "
            + format(run.summary["distance_to_peak_m"], ".6g")
            + " m",
            "white",
        ),
    ]
    for y, (text, color) in zip([18, 44, 70, 686], lines, strict=True):
        draw.text((24, y), text, fill=color, font_size=18)
    for y, text in zip(
        [720, 744, 768, 792, 820, 844, 868, 892, 930],
        [
            "Retained hour: " + run.inputs["datetime"] + " | engine: " + run.engine_version,
            "Grid peak lon, lat: "
            + ", ".join(format(v, ".6f") for v in run.summary["peak_location"]),
            "Wind FROM: "
            + format(run.summary["weather"]["wind_direction_deg"], ".6g")
            + " degrees | wind at 10 m: "
            + format(run.summary["weather"]["wind_speed_ms"], ".6g")
            + " m/s",
            "Source rates (g/s): "
            + ", ".join(format(s["emission_gs"], ".6g") for s in run.inputs["sources"]),
            "Primary PM2.5 only; flat terrain; steady state within the hour.",
            "Educational estimate, not a regulatory assessment. Hourly increment is not AQI.",
            "CPCB palette: <=30 green | <=60 light green | <=90 yellow | <=120 orange",
            "<=250 red | >250 dark red (ug/m3). Values <=1 transparent. No basemap in export.",
            "Input SHA256: " + run.inputs_hash,
        ],
        strict=True,
    ):
        draw.text((24, y), text, fill="#c1d2ce", font_size=14)
    metadata = PngImagePlugin.PngInfo()
    metadata.add_text("validation_status", validation_status(run))
    metadata.add_text("Description", " | ".join(text for text, _ in lines))
    stream = io.BytesIO()
    canvas.save(stream, format="PNG", pnginfo=metadata)
    return stream.getvalue()
