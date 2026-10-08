from datetime import UTC, datetime, timedelta

from django.conf import settings
from django.contrib.gis.geos import Polygon
from django.db.models import OuterRef, Subquery
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView
from rest_framework.pagination import CursorPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.warehouse.models import FireDetection, Reading, WeatherObservation

from .completeness import completeness
from .models import ObservationProvenance
from .units import IST, to_utc


class ObservationPagination(CursorPagination):
    page_size = 100
    ordering = "-observed_at"


class QuerySerializer(serializers.Serializer):
    start = serializers.DateTimeField(required=False)
    end = serializers.DateTimeField(required=False)
    station = serializers.IntegerField(min_value=1, required=False)
    pollutant = serializers.ChoiceField(
        choices=["pm25", "pm10", "no2", "so2", "co", "o3", "nh3"], required=False
    )
    city = serializers.SlugField(required=False)
    bbox = serializers.CharField(required=False)


def query_window(request):
    query = QuerySerializer(data=request.query_params)
    query.is_valid(raise_exception=True)
    data = query.validated_data
    end = data.get("end", datetime.now(UTC))
    start = data.get("start", end - timedelta(days=7))
    if start >= end or end - start > timedelta(days=settings.OBSERVATION_API_MAX_DAYS):
        raise ValidationError(
            f"Require start < end and range <= {settings.OBSERVATION_API_MAX_DAYS} days; "
            "end is exclusive."
        )
    return data, to_utc(start), to_utc(end)


class ReadingSerializer(serializers.ModelSerializer):
    source = serializers.IntegerField(source="ingestion_run.source_id", read_only=True)
    raw_unit = serializers.SerializerMethodField()

    class Meta:
        model = Reading
        fields = [
            "station",
            "pollutant",
            "observed_at",
            "value",
            "raw_value",
            "raw_unit",
            "quality_flag",
            "ingestion_run",
            "source",
        ]

    def get_raw_unit(self, obj) -> str | None:
        return obj.ingestion_run.params.get("raw_units", {}).get(
            f"{obj.station_id}:{obj.pollutant.code}"
        )


class WeatherSerializer(serializers.ModelSerializer):
    ingestion_run = serializers.IntegerField(source="provenance_run_id", read_only=True)

    class Meta:
        model = WeatherObservation
        fields = [
            "id",
            "city",
            "source",
            "observed_at",
            "temperature_c",
            "relative_humidity",
            "wind_speed_ms",
            "wind_dir_deg",
            "boundary_layer_height_m",
            "surface_pressure_hpa",
            "solar_radiation_wm2",
            "total_cloud_cover",
            "precipitation_mm",
            "ingestion_run",
        ]


class FireSerializer(serializers.ModelSerializer):
    ingestion_run = serializers.IntegerField(source="provenance_run_id", read_only=True)
    longitude = serializers.SerializerMethodField()
    latitude = serializers.SerializerMethodField()

    class Meta:
        model = FireDetection
        fields = [
            "id",
            "source",
            "detected_at",
            "longitude",
            "latitude",
            "satellite",
            "confidence",
            "frp",
            "ingestion_run",
        ]

    def get_longitude(self, obj) -> float:
        return obj.location.x

    def get_latitude(self, obj) -> float:
        return obj.location.y


PARAMETERS = [
    OpenApiParameter("start", type=str, description="ISO timestamp, inclusive"),
    OpenApiParameter("end", type=str, description="ISO timestamp, exclusive; maximum 31 days"),
]


@extend_schema(
    parameters=PARAMETERS
    + [OpenApiParameter("station", type=int), OpenApiParameter("pollutant", type=str)]
)
class ReadingView(ListAPIView):
    serializer_class = ReadingSerializer
    pagination_class = ObservationPagination

    def get_queryset(self):
        query, start, end = query_window(self.request)
        if "station" not in query:
            raise ValidationError("station is required")
        rows = Reading.objects.filter(
            station_id=query["station"], observed_at__gte=start, observed_at__lt=end
        )
        if "pollutant" in query:
            rows = rows.filter(pollutant__code=query["pollutant"])
        return rows.select_related("ingestion_run", "pollutant").order_by(
            "-observed_at", "pollutant_id"
        )


@extend_schema(parameters=PARAMETERS + [OpenApiParameter("city", type=str)])
class WeatherView(ListAPIView):
    serializer_class = WeatherSerializer
    pagination_class = ObservationPagination

    def get_queryset(self):
        query, start, end = query_window(self.request)
        if "city" not in query:
            raise ValidationError("city slug is required")
        provenance = ObservationProvenance.objects.filter(
            kind="weather", record_id=OuterRef("id"), observed_at=OuterRef("observed_at")
        )
        return (
            WeatherObservation.objects.filter(
                city__slug=query["city"], observed_at__gte=start, observed_at__lt=end
            )
            .annotate(provenance_run_id=Subquery(provenance.values("ingestion_run_id")[:1]))
            .order_by("-observed_at", "id")
        )


class FirePagination(ObservationPagination):
    ordering = "-detected_at"


@extend_schema(
    parameters=PARAMETERS
    + [OpenApiParameter("bbox", type=str, description="west,south,east,north in WGS84")]
)
class FireView(ListAPIView):
    serializer_class = FireSerializer
    pagination_class = FirePagination

    def get_queryset(self):
        query, start, end = query_window(self.request)
        try:
            west, south, east, north = [
                float(v) for v in query.get("bbox", settings.FIRMS_BBOX).split(",")
            ]
            if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
                raise ValueError
        except (ValueError, TypeError):
            raise ValidationError(
                "bbox must be west,south,east,north with valid increasing bounds"
            ) from None
        box = Polygon.from_bbox((west, south, east, north))
        box.srid = 4326
        provenance = ObservationProvenance.objects.filter(
            kind="fire", record_id=OuterRef("id"), observed_at=OuterRef("detected_at")
        )
        return (
            FireDetection.objects.filter(
                detected_at__gte=start, detected_at__lt=end, location__coveredby=box
            )
            .annotate(provenance_run_id=Subquery(provenance.values("ingestion_run_id")[:1]))
            .order_by("-detected_at", "id")
        )


class CompletenessView(APIView):
    @extend_schema(
        parameters=PARAMETERS + [OpenApiParameter("station", type=int)],
        responses=OpenApiTypes.OBJECT,
    )
    def get(self, request):
        query, start, end = query_window(request)
        report = completeness(
            str(start.astimezone(IST).date()),
            str((end - timedelta(microseconds=1)).astimezone(IST).date()),
            query.get("station"),
        )
        return Response(report)
