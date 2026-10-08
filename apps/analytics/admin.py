from django.contrib import admin

from .models import AnalysisRun, CityCoverage, CityMetric, PopulationRaster, StationEligibility


@admin.register(AnalysisRun)
class AnalysisRunAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "status", "started_at", "finished_at"]
    list_filter = ["name", "status", "started_at"]
    readonly_fields = [
        "parameters",
        "results",
        "git_commit",
        "started_at",
        "finished_at",
        "error_message",
    ]


@admin.register(StationEligibility)
class EligibilityAdmin(admin.ModelAdmin):
    list_display = ["station", "excluded_from_city", "excluded_from_spatial", "reason"]
    list_filter = ["excluded_from_city", "excluded_from_spatial"]


admin.site.register([CityCoverage, CityMetric, PopulationRaster])
