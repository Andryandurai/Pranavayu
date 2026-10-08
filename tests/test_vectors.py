import pytest
from django.contrib.postgres.search import SearchQuery, SearchVector
from django.db import DataError, connection, transaction
from pgvector.django import CosineDistance

from apps.rag.models import DocumentChunk
from tests.factories import DocumentFactory

pytestmark = [pytest.mark.django_db, pytest.mark.integration]


def test_1024_dimensional_vectors_and_cosine_ordering():
    document = DocumentFactory()
    target = [1.0] + [0.0] * 1023
    other = [0.0, 1.0] + [0.0] * 1022
    near = DocumentChunk.objects.create(
        document=document, chunk_index=0, page_start=1, page_end=1, text="test", embedding=target
    )
    far = DocumentChunk.objects.create(
        document=document, chunk_index=1, page_start=2, page_end=2, text="test", embedding=other
    )
    near.refresh_from_db()
    assert len(near.embedding) == 1024
    ordered = list(
        DocumentChunk.objects.annotate(distance=CosineDistance("embedding", target)).order_by(
            "distance"
        )
    )
    assert [chunk.pk for chunk in ordered] == [near.pk, far.pk]
    assert ordered[0].distance == pytest.approx(0)
    assert ordered[1].distance == pytest.approx(1)
    with pytest.raises((ValueError, DataError)), transaction.atomic():
        DocumentChunk.objects.create(
            document=document,
            chunk_index=2,
            page_start=3,
            page_end=3,
            text="test",
            embedding=[1.0] * 10,
        )


def test_hnsw_and_full_text_indexes():
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'rag_documentchunk'"
        )
        indexes = dict(cursor.fetchall())
    assert "USING hnsw" in indexes["chunk_embedding_hnsw"]
    assert "vector_cosine_ops" in indexes["chunk_embedding_hnsw"]
    assert "USING gin" in indexes["chunk_text_fts_gin"]
    document = DocumentFactory()
    chunk = DocumentChunk.objects.create(
        document=document,
        chunk_index=0,
        page_start=1,
        page_end=1,
        text="Air pollution affects health",
    )
    results = DocumentChunk.objects.annotate(search=SearchVector("text", config="english"))
    assert results.filter(search=SearchQuery("pollution", config="english")).get().pk == chunk.pk
