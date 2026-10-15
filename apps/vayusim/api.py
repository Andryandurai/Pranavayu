from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
from django.conf import settings
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiTypes, extend_schema
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.warehouse.models import City

from .artifacts import overlay_png
from .models import Scenario, ScenarioRun
from .presets import presets
from .serializers import RunSerializer
from .service import ensure_grid, run_response, run_scenario
from .weather import IST, background_stations


class RunView(APIView):
    @extend_schema(request=RunSerializer, responses=OpenApiTypes.OBJECT)
    def post(self, request):
        serializer = RunSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        run, cached = run_scenario(serializer.validated_data)
        return Response(run_response(run, cached))


class RunDetailView(APIView):
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request, run_id):
        return Response(
            run_response(
                get_object_or_404(ScenarioRun.objects.select_related("scenario"), pk=run_id)
            )
        )


class GridView(APIView):
    @extend_schema(responses=OpenApiTypes.BINARY)
    def get(self, request, run_id, kind):
        run = get_object_or_404(ScenarioRun, pk=run_id)
        ensure_grid(run)
        path = Path(settings.BASE_DIR) / run.grid_file_path
        if kind == "json":
            return Response(
                {
                    "run_id": run.pk,
                    "engine_version": run.engine_version,
                    "inputs_hash": run.inputs_hash,
                    **run.summary["grid"],
                    "units": "µg/m³",
                    "label": run.summary["label"],
                    "nodata": None,
                    "limitations": run.summary["limitations"],
                    "flags": run.flags,
                    "contours": run.summary.get("contours"),
                }
            )
        if kind == "png":
            values = np.fromfile(path, dtype="<f4").reshape(run.summary["grid"]["shape"])
            return HttpResponse(overlay_png(values), content_type="image/png")
        response = FileResponse(path.open("rb"), content_type="application/octet-stream")
        response["X-Grid-Header"] = f"/api/vayusim/grid/{run.pk}.json"
        return response


class ScenarioView(APIView):
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request, slug):
        scenario = get_object_or_404(Scenario, share_slug=slug)
        return Response(
            {
                "name": scenario.name,
                "slug": slug,
                "inputs": scenario.inputs,
                "runs": [run_response(r) for r in scenario.runs.order_by("id")],
            }
        )


class DayView(APIView):
    @extend_schema(request=RunSerializer, responses=OpenApiTypes.OBJECT)
    def post(self, request):
        serializer = RunSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        inputs = serializer.validated_data
        if inputs["weather_mode"] != "real":
            raise serializers.ValidationError("Day mode requires real hourly weather")
        start = (
            inputs["datetime"].astimezone(IST).replace(hour=0, minute=0, second=0, microsecond=0)
        )
        hours = []
        for hour in range(24):
            moment = start + timedelta(hours=hour)
            try:
                run, cached = run_scenario({**inputs, "datetime": moment}, materialize=False)
                hours.append(
                    {"datetime": moment.isoformat(), "available": True, **run_response(run, cached)}
                )
            except serializers.ValidationError as exc:
                hours.append(
                    {"datetime": moment.isoformat(), "available": False, "reason": str(exc.detail)}
                )
        return Response(
            {
                "date": start.date().isoformat(),
                "timezone": "Asia/Kolkata",
                "hours": hours,
                "label": "24 independent hourly increments; not daily/annual exposure",
                "grids": "Materialised on first grid request",
            }
        )


class PresetsView(APIView):
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        return Response({"presets": presets()})


class StationsView(APIView):
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        city = get_object_or_404(City, slug=request.query_params.get("city"))
        try:
            moment = datetime.fromisoformat(
                request.query_params.get("datetime", "").replace("Z", "+00:00")
            )
            if moment.tzinfo is None:
                raise ValueError
        except ValueError:
            raise serializers.ValidationError("Provide timezone-aware datetime") from None
        return Response(background_stations(city, moment, [city.location.x, city.location.y]))
