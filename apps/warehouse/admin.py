from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin

from apps.core.admin import CappedCountPaginator
from apps.core.admin_site import ReadOnlyCompositeAdmin

from .models import (
    City,
    District,
    FireDetection,
    Pollutant,
    Reading,
    State,
    Station,
    WeatherObservation,
)


@admin.register(State)
class StateAdmin(GISModelAdmin):
    list_display = ["name", "code"]
    search_fields = ["name", "code"]


@admin.register(District)
class DistrictAdmin(GISModelAdmin):
    list_display = ["name", "state", "census_code"]
    list_filter = ["state"]
    search_fields = ["name", "census_code"]
    list_select_related = ["state"]


@admin.register(City)
class CityAdmin(GISModelAdmin):
    list_display = ["name", "state", "is_ncap_nonattainment", "population", "slug"]
    list_filter = ["state", "is_ncap_nonattainment"]
    search_fields = ["name", "slug"]
    list_select_related = ["state"]
    prepopulated_fields = {"slug": ["name"]}


@admin.register(Pollutant)
class PollutantAdmin(admin.ModelAdmin):
    list_display = [
        "code",
        "display_name",
        "unit",
        "who_guideline_value",
        "who_averaging_hours",
        "naaqs_24h_value",
    ]
    search_fields = ["code", "display_name"]


@admin.register(Station)
class StationAdmin(GISModelAdmin):
    list_display = ["name", "external_id", "source", "city", "operator", "is_active", "last_seen"]
    list_filter = ["source", "is_active", "city"]
    search_fields = ["name", "external_id", "operator", "city__name"]
    list_select_related = ["source", "city"]


class HypertableAdmin(ReadOnlyCompositeAdmin, GISModelAdmin):
    paginator = CappedCountPaginator
    list_per_page = 100
    list_max_show_all = 0
    show_facets = admin.ShowFacets.NEVER
    change_list_template = "admin/core/capped_change_list.html"


@admin.register(Reading)
class ReadingAdmin(HypertableAdmin):
    list_display = [
        "station",
        "pollutant",
        "observed_at",
        "value",
        "raw_value",
        "quality_flag",
        "ingestion_run_id",
    ]
    list_filter = ["pollutant", "quality_flag", "observed_at"]
    search_fields = ["station__external_id", "station__name"]
    list_select_related = ["station", "pollutant", "ingestion_run"]


@admin.register(WeatherObservation)
class WeatherObservationAdmin(HypertableAdmin):
    list_display = [
        "city",
        "source",
        "observed_at",
        "temperature_c",
        "relative_humidity",
        "wind_speed_ms",
    ]
    list_filter = ["source", "observed_at"]
    search_fields = ["city__name"]
    list_select_related = ["city", "source"]


@admin.register(FireDetection)
class FireDetectionAdmin(HypertableAdmin):
    list_display = ["detected_at", "satellite", "confidence", "frp", "source"]
    list_filter = ["source", "satellite", "detected_at"]
    search_fields = ["satellite"]
    list_select_related = ["source"]
