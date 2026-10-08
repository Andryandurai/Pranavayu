import uuid

from django.contrib.gis.db import models
from django.db.models import F, Q

from apps.core.models import TimeStampedModel


class State(TimeStampedModel):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10, unique=True)
    geometry = models.MultiPolygonField(srid=4326, null=True, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class District(TimeStampedModel):
    name = models.CharField(max_length=150)
    state = models.ForeignKey(State, on_delete=models.PROTECT, related_name="districts")
    census_code = models.CharField(max_length=20, null=True, blank=True)
    geometry = models.MultiPolygonField(srid=4326, null=True, blank=True)

    class Meta:
        ordering = ["state__name", "name"]
        constraints = [
            models.UniqueConstraint(fields=["state", "name"], name="district_state_name_unique"),
            models.UniqueConstraint(
                fields=["census_code"],
                condition=Q(census_code__isnull=False),
                name="district_census_code_unique",
            ),
        ]

    def __str__(self):
        return f"{self.name}, {self.state}"


class City(TimeStampedModel):
    name = models.CharField(max_length=150)
    state = models.ForeignKey(State, on_delete=models.PROTECT, related_name="cities")
    location = models.PointField(srid=4326)
    is_ncap_nonattainment = models.BooleanField(default=False)
    population = models.PositiveBigIntegerField(null=True, blank=True)
    slug = models.SlugField(unique=True)

    class Meta:
        ordering = ["name", "pk"]
        constraints = [
            models.UniqueConstraint(fields=["state", "name"], name="city_state_name_unique")
        ]

    def __str__(self):
        return f"{self.name}, {self.state.code}"


class Pollutant(TimeStampedModel):
    class Code(models.TextChoices):
        PM25 = "pm25", "PM2.5"
        PM10 = "pm10", "PM10"
        NO2 = "no2", "NO2"
        SO2 = "so2", "SO2"
        CO = "co", "CO"
        O3 = "o3", "O3"
        NH3 = "nh3", "NH3"

    code = models.CharField(max_length=10, choices=Code, unique=True)
    display_name = models.CharField(max_length=100)
    unit = models.CharField(max_length=20)
    who_guideline_value = models.FloatField(null=True, blank=True)
    # The averaging period must accompany WHO values (O3 uses an 8-hour mean).
    who_averaging_hours = models.PositiveSmallIntegerField(null=True, blank=True)
    naaqs_24h_value = models.FloatField(null=True, blank=True)

    class Meta:
        ordering = ["code"]
        constraints = [
            models.CheckConstraint(
                condition=Q(code__in=["pm25", "pm10", "no2", "so2", "co", "o3", "nh3"]),
                name="pollutant_code_valid",
            ),
            models.CheckConstraint(
                condition=Q(who_guideline_value__isnull=True) | Q(who_guideline_value__gt=0),
                name="pollutant_who_positive",
            ),
            models.CheckConstraint(
                condition=Q(naaqs_24h_value__isnull=True) | Q(naaqs_24h_value__gt=0),
                name="pollutant_naaqs_positive",
            ),
        ]

    def __str__(self):
        return f"{self.display_name} ({self.unit})"


class Station(TimeStampedModel):
    external_id = models.CharField(max_length=150)
    source = models.ForeignKey(
        "ingest.DataSource", on_delete=models.PROTECT, related_name="stations"
    )
    name = models.CharField(max_length=255)
    city = models.ForeignKey(
        City, on_delete=models.PROTECT, null=True, blank=True, related_name="stations"
    )
    location = models.PointField(srid=4326)
    operator = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)
    first_seen = models.DateTimeField(null=True, blank=True)
    last_seen = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["name", "pk"]
        indexes = [models.Index(fields=["city", "is_active"], name="station_city_active_idx")]
        constraints = [
            models.UniqueConstraint(
                fields=["source", "external_id"], name="station_source_external_unique"
            ),
            models.CheckConstraint(
                condition=Q(first_seen__isnull=True)
                | Q(last_seen__isnull=True)
                | Q(last_seen__gte=F("first_seen")),
                name="station_seen_order",
            ),
        ]

    def __str__(self):
        return f"{self.name} [{self.external_id}]"


class Reading(models.Model):
    class QualityFlag(models.TextChoices):
        OK = "ok", "OK"
        MISSING = "missing", "Missing"
        NEGATIVE = "negative", "Negative"
        STUCK = "stuck", "Stuck"
        OUTLIER = "outlier", "Outlier"
        PM25_GT_PM10 = "pm25_gt_pm10", "PM2.5 > PM10"

    pk = models.CompositePrimaryKey("station_id", "pollutant_id", "observed_at")
    station = models.ForeignKey(Station, on_delete=models.PROTECT, related_name="readings")
    pollutant = models.ForeignKey(Pollutant, on_delete=models.PROTECT, related_name="readings")
    observed_at = models.DateTimeField()
    value = models.FloatField(null=True, blank=True)
    raw_value = models.FloatField(null=True, blank=True)
    quality_flag = models.CharField(max_length=15, choices=QualityFlag, default=QualityFlag.OK)
    ingestion_run = models.ForeignKey(
        "ingest.IngestionRun", on_delete=models.PROTECT, related_name="readings"
    )

    class Meta:
        ordering = ["-observed_at", "station_id", "pollutant_id"]
        indexes = [
            models.Index(fields=["station", "-observed_at"], name="reading_station_time_idx")
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(
                    quality_flag__in=[
                        "ok",
                        "missing",
                        "negative",
                        "stuck",
                        "outlier",
                        "pm25_gt_pm10",
                    ]
                ),
                name="reading_quality_valid",
            ),
            models.CheckConstraint(
                condition=~Q(quality_flag="ok") | Q(value__isnull=False, value__gte=0),
                name="reading_ok_value_present",
            ),
        ]

    def __str__(self):
        return f"{self.station_id}/{self.pollutant_id} @ {self.observed_at}: {self.value}"


class WeatherObservation(models.Model):
    pk = models.CompositePrimaryKey("id", "observed_at")
    id = models.UUIDField(default=uuid.uuid4, editable=False)
    city = models.ForeignKey(
        City, on_delete=models.PROTECT, null=True, blank=True, related_name="weather_observations"
    )
    location = models.PointField(srid=4326)
    observed_at = models.DateTimeField()
    temperature_c = models.FloatField(null=True, blank=True)
    relative_humidity = models.FloatField(null=True, blank=True)
    wind_speed_ms = models.FloatField(null=True, blank=True)
    wind_dir_deg = models.FloatField(null=True, blank=True)
    boundary_layer_height_m = models.FloatField(null=True, blank=True)
    surface_pressure_hpa = models.FloatField(null=True, blank=True)
    solar_radiation_wm2 = models.FloatField(null=True, blank=True)
    total_cloud_cover = models.FloatField(null=True, blank=True)
    precipitation_mm = models.FloatField(null=True, blank=True)
    source = models.ForeignKey(
        "ingest.DataSource", on_delete=models.PROTECT, related_name="weather_observations"
    )

    class Meta:
        ordering = ["-observed_at", "id"]
        indexes = [
            models.Index(fields=["city", "-observed_at"], name="weather_city_time_idx"),
            models.Index(fields=["source", "-observed_at"], name="weather_source_time_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(relative_humidity__isnull=True)
                | Q(relative_humidity__gte=0, relative_humidity__lte=100),
                name="weather_humidity_range",
            ),
            models.CheckConstraint(
                condition=Q(wind_dir_deg__isnull=True)
                | Q(wind_dir_deg__gte=0, wind_dir_deg__lt=360),
                name="weather_wind_dir_range",
            ),
            models.CheckConstraint(
                condition=Q(total_cloud_cover__isnull=True)
                | Q(total_cloud_cover__gte=0, total_cloud_cover__lte=1),
                name="weather_cloud_cover_range",
            ),
            *[
                models.CheckConstraint(
                    condition=Q(**{f"{field}__isnull": True}) | Q(**{f"{field}__gte": 0}),
                    name=f"weather_{name}_nonnegative",
                )
                for field, name in [
                    ("wind_speed_ms", "wind_speed"),
                    ("boundary_layer_height_m", "blh"),
                    ("precipitation_mm", "precip"),
                    ("surface_pressure_hpa", "pressure"),
                ]
            ],
        ]

    def __str__(self):
        return f"Weather @ {self.observed_at} ({self.source_id})"


class FireDetection(models.Model):
    pk = models.CompositePrimaryKey("id", "detected_at")
    id = models.UUIDField(default=uuid.uuid4, editable=False)
    detected_at = models.DateTimeField()
    location = models.PointField(srid=4326)
    satellite = models.CharField(max_length=100)
    confidence = models.CharField(max_length=20, blank=True)
    frp = models.FloatField(null=True, blank=True)
    source = models.ForeignKey(
        "ingest.DataSource", on_delete=models.PROTECT, related_name="fire_detections"
    )

    class Meta:
        ordering = ["-detected_at", "id"]
        indexes = [models.Index(fields=["source", "-detected_at"], name="fire_source_time_idx")]
        constraints = [
            models.CheckConstraint(
                condition=Q(frp__isnull=True) | Q(frp__gte=0), name="fire_frp_nonnegative"
            )
        ]

    def __str__(self):
        return f"{self.satellite} fire @ {self.detected_at}"
