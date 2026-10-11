import pytest

from apps.rag.evaluation import audit_answer
from apps.rag.models import Document, DocumentChunk, Query
from apps.rag.retrieval import citation


@pytest.mark.django_db
def test_audit_resolves_all_cited_chunks_on_same_page_without_hiding_invalid_identity():
    document = Document.objects.create(title="Fixture report", sha256="a" * 64)
    chunks = [
        DocumentChunk.objects.create(
            document=document,
            chunk_index=index,
            page_start=2,
            page_end=2,
            text=text,
        )
        for index, text in enumerate(
            ["The first reported value was 12.", "The second reported value was 34."]
        )
    ]
    references = [citation(chunk) for chunk in chunks]
    assert references[0]["label"] == references[1]["label"]
    answer = "\n".join(
        f"{chunk.text} [{reference['label']}]"
        for chunk, reference in zip(chunks, references, strict=True)
    )
    query = Query.objects.create(
        question="What were the two reported values?",
        route="literature",
        retrieved_ids=[chunk.pk for chunk in chunks],
        answer=answer,
        citations=references,
        provider="extractive",
    )
    result = {"query_id": query.pk, "answer": answer, "citations": references, "tool_results": []}
    assert audit_answer(result) == {
        "sentences": 2,
        "supported_sentences": 2,
        "citation_uses": 2,
        "correct_citation_uses": 2,
    }
    result["citations"][1]["sha256"] = "b" * 64
    invalid = audit_answer(result)
    assert invalid["correct_citation_uses"] == 0
    assert invalid["supported_sentences"] == 0
