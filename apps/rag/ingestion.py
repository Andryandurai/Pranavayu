"""Content-idempotent parsing and batch-resumable embedding over real local inputs."""

from pathlib import Path

from django.conf import settings
from django.db import connection, transaction
from django.utils import timezone

from apps.warehouse.models import City, Pollutant

from .chunking import chunk_pages, mentions
from .encoders import EMBED_MODEL, EMBED_REVISION, computation_revision, get_models, tokenizer
from .library import digest_file
from .models import Document, DocumentChunk, DocumentPage
from .parsing import PARSER_VERSION, parse_source


def document_path(document):
    if document.source_path:
        path = (settings.BASE_DIR / document.source_path).resolve()
        if not path.is_relative_to(settings.BASE_DIR.resolve()):
            raise ValueError("Document source must remain inside the project")
        return path
    if document.file:
        return Path(document.file.path)
    raise ValueError("Document has no stored body")


def ingest(document_id, embed=True, models=None, source_tokenizer=None):
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_try_advisory_lock(%s, %s)", [56205, document_id])
        if not cursor.fetchone()[0]:
            return {
                "document": document_id,
                "status": "already_running",
                "parsed": 0,
                "embedded": 0,
            }
    try:
        return ingest_locked(document_id, embed, models, source_tokenizer)
    finally:
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_unlock(%s, %s)", [56205, document_id])


def ingest_locked(document_id, embed, models, source_tokenizer):
    document = Document.objects.get(pk=document_id)
    parsed, embedded = 0, 0
    try:
        path = document_path(document)
        if digest_file(path) != document.sha256:
            raise ValueError("Stored body differs from SHA256; register a new document revision")
        already_parsed = (
            document.ingestion_metadata.get("parsed_sha256") == document.sha256
            and document.ingestion_metadata.get("parser_version") == PARSER_VERSION
        )
        pending = document.chunks.filter(embedding__isnull=True)
        fingerprint = computation_revision(EMBED_REVISION)
        if (
            embed
            and already_parsed
            and document.ingestion_metadata.get("embedding_fingerprint") != fingerprint
        ):
            document.chunks.update(embedding=None)
        if already_parsed and (not embed or not pending.exists()):
            if embed and document.status != Document.Status.READY:
                document.status = Document.Status.READY
                document.error_message = ""
                document.save(update_fields=["status", "error_message", "updated_at"])
            return {"document": document.pk, "status": "unchanged", "parsed": 0, "embedded": 0}
        if not already_parsed:
            document.status = Document.Status.PARSING
            document.save(update_fields=["status", "updated_at"])
            pages = parse_source(path, document.source_format)
            chunks = chunk_pages(pages, source_tokenizer or tokenizer())
            if not pages or not chunks:
                raise ValueError("No source text could be parsed into evidence chunks")
            doi = document.ingestion_metadata.get("doi")
            all_text = "\n".join(page.text for page in pages)
            if doi and doi.casefold() not in all_text.casefold():
                raise ValueError("Expected DOI absent: inspect identity before indexing this body")
            cities = list(City.objects.values_list("slug", "name"))
            pollutants = list(Pollutant.objects.values_list("code", flat=True))
            with transaction.atomic():
                document.pages.all().delete()
                document.chunks.all().delete()
                DocumentPage.objects.bulk_create(
                    [
                        DocumentPage(
                            document=document,
                            page_number=page.number,
                            text=page.text,
                            sections=page.sections,
                            tables=page.tables,
                            is_ocr=page.is_ocr,
                            is_logical_page=page.is_logical,
                        )
                        for page in pages
                    ]
                )
                objects = []
                for chunk in chunks:
                    tags = mentions(chunk["text"], cities, pollutants)
                    declared = document.ingestion_metadata.get("declared_city")
                    if declared and declared not in tags["cities"]:
                        tags["cities"].append(declared)
                    objects.append(
                        DocumentChunk(
                            document=document,
                            chunk_index=chunk["chunk_index"],
                            page_start=chunk["page_start"],
                            page_end=chunk["page_end"],
                            section_title=chunk["section_title"][:500],
                            text=chunk["text"],
                            token_count=chunk["token_count"],
                            metadata={
                                **tags,
                                "year": document.year,
                                "category": document.category,
                                "is_table": chunk["is_table"],
                                "is_logical_page": chunk["is_logical_page"],
                                "source_sha256": document.sha256,
                            },
                        )
                    )
                DocumentChunk.objects.bulk_create(objects)
                document.page_count = len(pages)
                document.parsed_at = timezone.now()
                document.status = Document.Status.PARSED
                document.error_message = ""
                document.ingestion_metadata.update(
                    parsed_sha256=document.sha256,
                    ocr_pages=sum(p.is_ocr for p in pages),
                    logical_pages=bool(pages[0].is_logical),
                    parser="PyMuPDF/pdfplumber/Tesseract/HTML/Markdown",
                    parser_version=PARSER_VERSION,
                    embedding_model=EMBED_MODEL,
                    embedding_revision=EMBED_REVISION,
                )
                document.save()
            parsed = len(chunks)
        if embed:
            document.status = Document.Status.EMBEDDING
            document.ingestion_metadata["embedding_fingerprint"] = fingerprint
            document.save(update_fields=["status", "ingestion_metadata", "updated_at"])
            model = models or get_models()
            while True:
                batch = list(
                    document.chunks.filter(embedding__isnull=True).order_by("chunk_index")[:8]
                )
                if not batch:
                    break
                vectors = model.embed([chunk.text for chunk in batch])
                for chunk, vector in zip(batch, vectors, strict=True):
                    chunk.embedding = vector
                DocumentChunk.objects.bulk_update(batch, ["embedding"])
                embedded += len(batch)
            document.status = Document.Status.READY
            document.error_message = ""
            document.save(update_fields=["status", "error_message", "updated_at"])
        return {
            "document": document.pk,
            "status": document.status,
            "parsed": parsed,
            "embedded": embedded,
        }
    except Exception as exc:
        document.status = Document.Status.FAILED
        document.error_message = f"{type(exc).__name__}: {exc}"[:2000]
        document.save(update_fields=["status", "error_message", "updated_at"])
        raise
