from django.contrib import admin
from django.db import transaction
from django.utils import timezone

from .forms import DocumentForm
from .models import Document, DocumentChunk, DocumentPage, Query


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    form = DocumentForm
    list_display = ["title", "year", "category", "status", "page_count", "parsed_at"]
    list_filter = ["category", "year"]
    search_fields = ["title", "authors", "sha256"]
    readonly_fields = [
        "sha256",
        "status",
        "page_count",
        "parsed_at",
        "source_path",
        "source_format",
        "size_bytes",
        "retrieved_at",
        "error_message",
        "ingestion_metadata",
        "created_at",
        "updated_at",
    ]
    actions = ["ingest_selected"]

    def get_readonly_fields(self, request, obj=None):
        return [*self.readonly_fields, *(["file"] if obj else [])]

    def save_model(self, request, obj, form, change):
        if not change:
            obj.source_format = "pdf"
            obj.retrieved_at = timezone.now()
        super().save_model(request, obj, form, change)
        for chunk in obj.chunks.all():
            chunk.metadata.update(year=obj.year, category=obj.category)
            chunk.save(update_fields=["metadata", "updated_at"])
        from .tasks import ingest_document

        transaction.on_commit(lambda: ingest_document.delay(obj.pk))

    @admin.action(description="Parse and embed selected PDFs (resume unchanged inputs)")
    def ingest_selected(self, request, queryset):
        from .tasks import ingest_document

        identifiers = list(queryset.values_list("pk", flat=True))
        for identifier in identifiers:
            transaction.on_commit(lambda pk=identifier: ingest_document.delay(pk))
        self.message_user(request, f"Queued {len(identifiers)} document ingestion tasks")


@admin.register(DocumentChunk)
class DocumentChunkAdmin(admin.ModelAdmin):
    list_display = [
        "document",
        "chunk_index",
        "page_start",
        "page_end",
        "section_title",
        "token_count",
    ]
    list_filter = ["document__category"]
    search_fields = ["document__title", "section_title", "text"]
    list_select_related = ["document"]
    readonly_fields = ["embedding", "created_at", "updated_at"]


@admin.register(DocumentPage)
class DocumentPageAdmin(admin.ModelAdmin):
    list_display = ["document", "page_number", "is_ocr", "is_logical_page"]
    readonly_fields = [
        "document",
        "page_number",
        "text",
        "sections",
        "tables",
        "is_ocr",
        "is_logical_page",
        "created_at",
        "updated_at",
    ]

    def has_add_permission(self, request):
        return False


@admin.register(Query)
class QueryAdmin(admin.ModelAdmin):
    list_display = ["id", "route", "provider", "latency_ms", "created_at"]
    readonly_fields = [field.name for field in Query._meta.fields]

    def has_add_permission(self, request):
        return False
