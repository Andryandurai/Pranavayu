from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVector
from django.core.validators import FileExtensionValidator, RegexValidator
from django.db import models
from django.db.models import F, Q
from pgvector.django import HnswIndex, VectorField

from apps.core.models import TimeStampedModel


class Document(TimeStampedModel):
    class Status(models.TextChoices):
        DOWNLOADED = "downloaded", "Downloaded"
        PARSING = "parsing", "Parsing"
        PARSED = "parsed", "Parsed"
        EMBEDDING = "embedding", "Embedding"
        READY = "ready", "Ready"
        FAILED = "failed", "Failed"

    class Category(models.TextChoices):
        POLICY = "policy", "Policy"
        STANDARD = "standard", "Standard"
        DISPERSION = "dispersion", "Dispersion"
        SOURCE_APPORTIONMENT = "source_apportionment", "Source apportionment"
        METHODS = "methods", "Methods"
        HEALTH = "health", "Health"
        CITY_PLAN = "city_plan", "City plan"
        PROJECT_RESULTS = "project_results", "Project results"
        OTHER = "other", "Other"

    title = models.CharField(max_length=500)
    authors = models.TextField(blank=True)
    year = models.PositiveSmallIntegerField(null=True, blank=True)
    category = models.CharField(max_length=25, choices=Category, default=Category.OTHER)
    source_url = models.URLField(max_length=1000, blank=True)
    licence_note = models.TextField(blank=True)
    file = models.FileField(
        upload_to="documents/%Y/%m/",
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=["pdf"])],
    )
    sha256 = models.CharField(
        max_length=64,
        unique=True,
        validators=[RegexValidator(r"^[0-9a-f]{64}$", "Use a lowercase SHA-256 hex digest.")],
    )
    page_count = models.PositiveIntegerField(null=True, blank=True)
    parsed_at = models.DateTimeField(null=True, blank=True)
    source_path = models.CharField(max_length=1000, blank=True)
    source_format = models.CharField(max_length=10, default="pdf")
    size_bytes = models.PositiveBigIntegerField(null=True, blank=True)
    retrieved_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status, default=Status.DOWNLOADED)
    error_message = models.TextField(blank=True)
    ingestion_metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["title", "pk"]
        indexes = [models.Index(fields=["category", "year"], name="document_category_year_idx")]
        constraints = [
            models.CheckConstraint(
                condition=Q(page_count__isnull=True) | Q(page_count__gt=0),
                name="document_pages_positive",
            )
        ]

    def __str__(self):
        return self.title


class DocumentChunk(TimeStampedModel):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="chunks")
    chunk_index = models.PositiveIntegerField()
    page_start = models.PositiveIntegerField()
    page_end = models.PositiveIntegerField()
    section_title = models.CharField(max_length=500, blank=True)
    text = models.TextField()
    token_count = models.PositiveIntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)
    embedding = VectorField(dimensions=1024, null=True, blank=True)

    class Meta:
        ordering = ["document_id", "chunk_index"]
        indexes = [
            HnswIndex(
                name="chunk_embedding_hnsw",
                fields=["embedding"],
                m=16,
                ef_construction=64,
                opclasses=["vector_cosine_ops"],
            ),
            GinIndex(SearchVector("text", config="english"), name="chunk_text_fts_gin"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["document", "chunk_index"], name="chunk_document_index_unique"
            ),
            models.CheckConstraint(
                condition=Q(page_start__gte=1) & Q(page_end__gte=F("page_start")),
                name="chunk_page_range_valid",
            ),
        ]

    def __str__(self):
        return (
            f"{self.document_id}: chunk {self.chunk_index}, pp. {self.page_start}-{self.page_end}"
        )


class DocumentPage(TimeStampedModel):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="pages")
    page_number = models.PositiveIntegerField()
    text = models.TextField()
    sections = models.JSONField(default=list, blank=True)
    tables = models.JSONField(default=list, blank=True)
    is_ocr = models.BooleanField(default=False)
    is_logical_page = models.BooleanField(default=False)

    class Meta:
        ordering = ["document_id", "page_number"]
        constraints = [
            models.UniqueConstraint(fields=["document", "page_number"], name="rag_page_unique"),
            models.CheckConstraint(condition=Q(page_number__gte=1), name="rag_page_positive"),
        ]


class Query(TimeStampedModel):
    question = models.TextField()
    filters = models.JSONField(default=dict)
    route = models.CharField(max_length=12)
    retrieved_ids = models.JSONField(default=list)
    tool_calls = models.JSONField(default=list)
    answer = models.TextField()
    citations = models.JSONField(default=list)
    provider = models.CharField(max_length=20)
    latency_ms = models.PositiveIntegerField(default=0)
    verification = models.JSONField(default=dict)

    class Meta:
        ordering = ["-pk"]
