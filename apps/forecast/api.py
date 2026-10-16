from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from rest_framework import serializers
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.analytics.models import AnalysisRun
from apps.warehouse.models import City

from .models import Forecast, ForecastEvaluation
from .serving import served_forecast


class ForecastSerializer(serializers.ModelSerializer):
    algorithm = serializers.CharField(source="model_version.algorithm", read_only=True)
    cohort = serializers.CharField(source="model_version.cohort", read_only=True)
    mlflow_run_id = serializers.CharField(source="model_version.mlflow_run_id", read_only=True)
    interval_policy = serializers.JSONField(source="model_version.interval_policy", read_only=True)
    forecast_method = serializers.CharField(read_only=True)
    policy_source = serializers.CharField(read_only=True)
    fallback_used = serializers.BooleanField(read_only=True)
    fallback_reason = serializers.CharField(read_only=True, allow_null=True)

    def to_representation(self, instance):
        result = super().to_representation(instance)
        result.update(served_forecast(instance))
        fields = ("forecast_method", "policy_source", "fallback_used", "fallback_reason")
        return {**{key: result.pop(key) for key in fields}, **result}

    class Meta:
        model = Forecast
        fields = [
            "id",
            "issued_for_date",
            "target_date",
            "horizon",
            "point",
            "lower80",
            "upper80",
            "lower95",
            "upper95",
            "aqi_category",
            "mode",
            "model_version",
            "algorithm",
            "cohort",
            "mlflow_run_id",
            "top_drivers",
            "feature_provenance",
            "interval_policy",
            "forecast_method",
            "policy_source",
            "fallback_used",
            "fallback_reason",
        ]


def completed_run():
    run = AnalysisRun.objects.filter(name="phase4", status="success").order_by("-pk").first()
    if run is None:
        raise NotFound("No completed Phase 4 forecasting run")
    return run


class LatestView(APIView):
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request, slug):
        city = get_object_or_404(City, slug=slug)
        run = completed_run()
        rows = Forecast.objects.filter(city=city, model_version__analysis_run=run).select_related(
            "model_version", "city"
        )
        last = rows.order_by("-issued_for_date").first()
        if last is None:
            raise NotFound("No issued forecasts for this city")
        rows = rows.filter(issued_for_date=last.issued_for_date).order_by("horizon", "-id")
        return Response(
            {
                "city": slug,
                "run": run.pk,
                "category_scope": "CPCB PM2.5 subindex category; not overall AQI",
                "forecasts": ForecastSerializer(rows, many=True).data,
            }
        )


class HistoryView(APIView):
    @extend_schema(
        parameters=[
            OpenApiParameter("start", type=OpenApiTypes.DATE),
            OpenApiParameter("end", type=OpenApiTypes.DATE),
        ],
        responses=OpenApiTypes.OBJECT,
    )
    def get(self, request, slug):
        class Query(serializers.Serializer):
            start = serializers.DateField(required=True)
            end = serializers.DateField(required=True)

            def validate(self, data):
                if not 0 <= (data["end"] - data["start"]).days <= 366:
                    raise serializers.ValidationError("Use an ordered date interval up to 366 days")
                return data

        query = Query(data=request.query_params)
        query.is_valid(raise_exception=True)
        city = get_object_or_404(City, slug=slug)
        run = completed_run()
        rows = (
            Forecast.objects.filter(
                city=city,
                model_version__analysis_run=run,
                target_date__range=(query.validated_data["start"], query.validated_data["end"]),
            )
            .select_related("model_version", "city")
            .order_by("target_date", "horizon")
        )
        return Response(
            {
                "city": slug,
                "run": run.pk,
                "date_filter": "target_date inclusive",
                "forecasts": ForecastSerializer(rows, many=True).data,
            }
        )


class EvaluationView(APIView):
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request, slug):
        city = get_object_or_404(City, slug=slug)
        run = completed_run()
        rows = list(
            ForecastEvaluation.objects.filter(city=city, analysis_run=run)
            .order_by("horizon")
            .values_list("result", flat=True)
        )
        if not rows:
            raise NotFound("No evaluation for this city")
        return Response(
            {"city": slug, "run": run.pk, "headline_weather": "archived_forecast", "results": rows}
        )
