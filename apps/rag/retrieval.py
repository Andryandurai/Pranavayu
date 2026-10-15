"""pgvector cosine + indexed English full-text ranking, RRF and pinned reranking."""

import os

from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from pgvector.django import CosineDistance
from rest_framework import serializers

from apps.warehouse.models import City

from .encoders import get_models
from .formatting import terms
from .models import Document, DocumentChunk


class Filters(serializers.Serializer):
    category = serializers.ChoiceField(choices=Document.Category.values, required=False)
    year_min = serializers.IntegerField(min_value=1900, max_value=2100, required=False)
    year_max = serializers.IntegerField(min_value=1900, max_value=2100, required=False)
    city = serializers.SlugField(required=False)

    def to_internal_value(self, data):
        if not isinstance(data, dict) or set(data) - set(self.fields):
            raise serializers.ValidationError({"filters": "Use known filter fields in an object"})
        return super().to_internal_value(data)

    def validate_city(self, value):
        if not City.objects.filter(slug=value).exists():
            raise serializers.ValidationError("Unknown seeded city")
        return value

    def validate(self, attrs):
        if attrs.get("year_min", 1900) > attrs.get("year_max", 2100):
            raise serializers.ValidationError("year_min must not exceed year_max")
        return attrs


def validate_filters(filters):
    serializer = Filters(data=filters or {})
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data


def reciprocal_rank_fusion(rankings, k=60):
    scores = {}
    for ranking in rankings:
        seen = set()
        for position, identifier in enumerate(ranking, 1):
            if identifier not in seen:
                scores[identifier] = scores.get(identifier, 0) + 1 / (k + position)
                seen.add(identifier)
    return sorted(scores, key=lambda identifier: (-scores[identifier], identifier)), scores


def corpus(filters):
    rows = DocumentChunk.objects.filter(document__status=Document.Status.READY).select_related(
        "document"
    )
    for field, value in filters.items():
        if field == "category":
            rows = rows.filter(document__category=value)
        elif field == "year_min":
            rows = rows.filter(document__year__gte=value)
        elif field == "year_max":
            rows = rows.filter(document__year__lte=value)
        elif field == "city":
            rows = rows.filter(metadata__cities__contains=[value])
    return rows


def citation(chunk):
    title = chunk.document.title.replace("[", "(").replace("]", ")")
    if chunk.metadata.get("is_logical_page"):
        location = f"§ {chunk.section_title}" if chunk.section_title else "unpaginated text"
    else:
        location = f"p. {chunk.page_start}"
        if chunk.page_end != chunk.page_start:
            location += f"–{chunk.page_end}"
    return {
        "id": f"chunk:{chunk.pk}",
        "label": f"{title}, {location}",
        "kind": "document",
        "document_id": chunk.document_id,
        "chunk_id": chunk.pk,
        "title": chunk.document.title,
        "page_start": chunk.page_start,
        "page_end": chunk.page_end,
        "section_title": chunk.section_title,
        "is_logical_page": chunk.metadata.get("is_logical_page", False),
        "source_url": chunk.document.source_url,
        "url": f"/api/rag/documents/{chunk.document_id}/page/{chunk.page_start}/",
        "sha256": chunk.document.sha256,
    }


def retrieve(
    question, filters=None, mode="hybrid_rerank", limit=8, models=None, rerank_candidates=None
):
    if mode not in {"vector", "keyword", "hybrid", "hybrid_rerank"}:
        raise ValueError("Unknown retrieval mode")
    filters = validate_filters(filters)
    rows = corpus(filters)
    if not rows.exists():
        return []
    model = models or get_models()
    vectors, keywords = [], []
    if mode != "keyword":
        vector = model.embed_query(question)
        vectors = list(
            rows.filter(embedding__isnull=False)
            .annotate(distance=CosineDistance("embedding", vector))
            .order_by("distance")[:40]
        )
    if mode != "vector":
        query_text = " OR ".join(sorted(terms(question))) or question
        query = SearchQuery(query_text, config="english", search_type="websearch")
        search = SearchVector("text", config="english")
        keywords = list(
            rows.annotate(search=search, rank=SearchRank(search, query, normalization=32))
            .filter(search=query)
            .order_by("-rank", "pk")[:40]
        )
    if mode == "vector":
        selected = vectors
    elif mode == "keyword":
        selected = keywords
    else:
        identifiers, scores = reciprocal_rank_fusion(
            [[chunk.pk for chunk in vectors], [chunk.pk for chunk in keywords]]
        )
        lookup = {chunk.pk: chunk for chunk in [*vectors, *keywords]}
        selected = [lookup[identifier] for identifier in identifiers[:40]]
        for chunk in selected:
            chunk.fusion_score = scores[chunk.pk]
    if mode == "hybrid_rerank" and selected:
        candidates = int(rerank_candidates or os.environ.get("RAG_RERANK_CANDIDATES", "40"))
        if not 10 <= candidates <= 40:
            raise ValueError("Use 10–40 reranking candidates")
        selected = selected[:candidates]
        scores = model.rerank(question, [chunk.text for chunk in selected])
        for chunk, score in zip(selected, scores, strict=True):
            chunk.rerank_score = float(score)
        selected = sorted(selected, key=lambda chunk: (-chunk.rerank_score, chunk.pk))
    return [
        {
            "chunk_id": chunk.pk,
            "text": chunk.text,
            "citation": citation(chunk),
            "rerank_score": getattr(chunk, "rerank_score", None),
            "fusion_score": getattr(chunk, "fusion_score", None),
            "distance": float(chunk.distance) if hasattr(chunk, "distance") else None,
        }
        for chunk in selected[:limit]
    ]
