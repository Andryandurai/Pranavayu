from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from rest_framework import serializers
from rest_framework.exceptions import NotFound
from rest_framework.generics import ListAPIView
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.warehouse.models import City

from .models import AnalysisRun, CityCoverage, CityMetric, CitySeries


class Query(serializers.Serializer):
    run = serializers.IntegerField(min_value=1, required=False)
    kind = serializers.ChoiceField(choices=["raw", "deweathered"], default="raw")
    freq = serializers.ChoiceField(choices=["daily", "monthly"], default="daily")
    city = serializers.SlugField(required=False)
    pollutant = serializers.ChoiceField(
        choices=["pm25", "pm10", "co", "no2", "so2", "o3", "nh3"], default="pm25"
    )
    start = serializers.DateField(required=False)
    end = serializers.DateField(required=False)


def query_run(request):
    query = Query(data=request.query_params)
    query.is_valid(raise_exception=True)
    params = query.validated_data
    rows = AnalysisRun.objects.filter(status="success", name="phase3a")
    if "run" in params:
        rows = rows.filter(pk=params["run"])
    run = rows.order_by("-id").first()
    if run is None:
        raise NotFound("No completed Phase 3A analysis run")
    return params, run


class Pagination(LimitOffsetPagination):
    default_limit = 100
    max_limit = 1000


class CoverageSerializer(serializers.ModelSerializer):
    city = serializers.CharField(source="city.slug")
    pollutant = serializers.CharField(source="pollutant.code")

    class Meta:
        model = CityCoverage
        fields = [
            "run",
            "city",
            "pollutant",
            "year",
            "hours_present",
            "hours_expected",
            "valid_days",
            "expected_days",
            "valid_months",
            "eligible",
        ]


class SeriesSerializer(serializers.ModelSerializer):
    city = serializers.CharField(source="city.slug")
    pollutant = serializers.CharField(source="pollutant.code")

    class Meta:
        model = CitySeries
        fields = [
            "run",
            "city",
            "pollutant",
            "kind",
            "frequency",
            "date",
            "value",
            "valid_count",
            "expected_count",
            "sampling_se",
        ]


@extend_schema(
    parameters=[
        OpenApiParameter("city", type=str),
        OpenApiParameter("pollutant", type=str),
        OpenApiParameter("run", type=int),
    ]
)
class CoverageView(ListAPIView):
    serializer_class = CoverageSerializer
    pagination_class = Pagination

    def get_queryset(self):
        params, run = query_run(self.request)
        rows = CityCoverage.objects.filter(run=run, pollutant__code=params["pollutant"])
        if "city" in params:
            rows = rows.filter(city__slug=params["city"])
        return rows.select_related("city", "pollutant").order_by("city__slug", "year")


class SummaryView(APIView):
    @extend_schema(parameters=[OpenApiParameter("run", type=int)], responses=OpenApiTypes.OBJECT)
    def get(self, request, slug):
        _, run = query_run(request)
        city = get_object_or_404(City, slug=slug)
        results = list(
            CityMetric.objects.filter(run=run, city=city)
            .order_by("name", "year", "id")
            .values("name", "year", "result")
        )
        return Response(
            {
                "run": run.pk,
                "city": slug,
                "data_window": [run.data_start, run.data_end],
                "parameters": run.parameters,
                "metrics": results,
            }
        )


@extend_schema(
    parameters=[
        OpenApiParameter("kind", type=str, enum=["raw", "deweathered"]),
        OpenApiParameter("freq", type=str, enum=["daily", "monthly"]),
        OpenApiParameter("run", type=int),
        OpenApiParameter("start", type=str),
        OpenApiParameter("end", type=str),
    ]
)
class SeriesView(ListAPIView):
    serializer_class = SeriesSerializer
    pagination_class = Pagination

    def get_queryset(self):
        params, run = query_run(self.request)
        city = get_object_or_404(City, slug=self.kwargs["slug"])
        rows = CitySeries.objects.filter(
            run=run,
            city=city,
            pollutant__code=params["pollutant"],
            kind=params["kind"],
            frequency=params["freq"],
        )
        if "start" in params:
            rows = rows.filter(date__gte=params["start"])
        if "end" in params:
            rows = rows.filter(date__lt=params["end"])
        if "start" in params and "end" in params and params["start"] >= params["end"]:
            raise serializers.ValidationError("start must precede exclusive end")
        return rows.select_related("city", "pollutant").order_by("date")
