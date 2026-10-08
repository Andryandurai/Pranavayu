from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVector
from django.core.validators import FileExtensionValidator, RegexValidator
from django.db import models
from django.db.models import F, Q
from pgvector.django import HnswIndex, VectorField

from apps.core.models import TimeStampedModel


class Document(TimeStampedModel):
    class Category(models.TextChoices):
        POLICY = "policy", "Policy"
        STANDARD = "standard", "Standard"
        DISPERSION = "dispersion", "Dispersion"
        SOURCE_APPORTIONMENT = "source_apportionment", "Source apportionment"
        METHODS = "methods", "Methods"
        HEALTH = "health", "Health"
        CITY_PLAN = "city_plan", "City plan"
        OTHER = "other", "Other"

    title = models.CharField(max_length=500)
    authors = models.TextField(blank=True)
    year = models.PositiveSmallIntegerField(null=True, blank=True)
    category = models.CharField(max_length=25, choices=Category, default=Category.OTHER)
    source_url = models.URLField(max_length=1000, blank=True)
    licence_note = models.TextField(blank=True)
    file = models.FileField(
        upload_to="documents/%Y/%m/",
        validators=[FileExtensionValidator(allowed_extensions=["pdf"])],
    )
    sha256 = models.CharField(
        max_length=64,
        unique=True,
        validators=[RegexValidator(r"^[0-9a-f]{64}$", "Use a lowercase SHA-256 hex digest.")],
    )
    page_count = models.PositiveIntegerField(null=True, blank=True)
    parsed_at = models.DateTimeField(null=True, blank=True)

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
