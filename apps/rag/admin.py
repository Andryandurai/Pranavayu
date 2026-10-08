from django.contrib import admin

from .models import Document, DocumentChunk


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ["title", "year", "category", "page_count", "parsed_at"]
    list_filter = ["category", "year"]
    search_fields = ["title", "authors", "sha256"]
    readonly_fields = ["created_at", "updated_at"]


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
