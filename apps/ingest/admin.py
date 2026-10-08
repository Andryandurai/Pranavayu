from django.contrib import admin

from .models import (
    BoundaryProvenance,
    CityDistrictLink,
    DataSource,
    IngestionRun,
    ObservationProvenance,
    RawAsset,
)


@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "access_method", "is_active", "url"]
    list_filter = ["access_method", "is_active"]
    search_fields = ["name", "slug", "description"]
    prepopulated_fields = {"slug": ["name"]}


@admin.register(IngestionRun)
class IngestionRunAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "source",
        "task_name",
        "status",
        "started_at",
        "finished_at",
        "rows_fetched",
        "rows_inserted",
        "rows_flagged",
    ]
    list_filter = ["status", "source", "started_at"]
    search_fields = ["task_name", "source__name", "error_message"]
    list_select_related = ["source"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(RawAsset)
class RawAssetAdmin(admin.ModelAdmin):
    list_display = ["source", "path", "size_bytes", "sha256", "ingestion_run"]
    list_filter = ["source", "created_at"]
    search_fields = ["path", "sha256", "download_url"]
    list_select_related = ["source", "ingestion_run"]


@admin.register(ObservationProvenance)
class ObservationProvenanceAdmin(admin.ModelAdmin):
    list_display = ["kind", "record_id", "observed_at", "source", "ingestion_run"]
    list_filter = ["kind", "source", "observed_at"]
    search_fields = ["=record_id"]
    list_select_related = ["source", "ingestion_run"]
    show_full_result_count = False


@admin.register(CityDistrictLink)
class CityDistrictLinkAdmin(admin.ModelAdmin):
    list_display = ["city", "district", "ingestion_run"]
    list_filter = ["district__state"]
    search_fields = ["city__name", "district__name"]
    list_select_related = ["city", "district", "ingestion_run"]


@admin.register(BoundaryProvenance)
class BoundaryProvenanceAdmin(admin.ModelAdmin):
    list_display = ["state", "district", "asset", "ingestion_run"]
    list_select_related = ["state", "district", "asset", "ingestion_run"]
