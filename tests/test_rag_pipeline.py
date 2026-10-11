import hashlib
import re
from datetime import date
from unittest.mock import Mock

import pytest
from django.test import override_settings
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.analytics.models import AnalysisRun, CityCoverage, CityMetric, CitySeries
from apps.rag import ingestion, service
from apps.rag.chunking import chunk_pages, window_chunks
from apps.rag.data_tools import call_tool
from apps.rag.models import Document, DocumentChunk, DocumentPage, Query
from apps.rag.parsing import parse_pdf
from apps.rag.providers import Provider, choose_provider
from apps.rag.retrieval import reciprocal_rank_fusion, retrieve, validate_filters
from apps.rag.verification import REFUSAL, verify_answer
from tests.factories import CityFactory, DocumentFactory, PollutantFactory


class FixtureTokenizer:
    def __call__(self, text, **kwargs):
        offsets = [(match.start(), match.end()) for match in re.finditer(r"\S+", text)]
        return {"input_ids": list(range(len(offsets))), "offset_mapping": offsets}


def fixture_pdf(path):
    import pymupdf

    with pymupdf.open() as pdf:
        for n in (1, 2):
            page = pdf.new_page()
            page.insert_text((50, 50), f"Section {n}: Meteorology", fontsize=20)
            page.insert_text(
                (50, 90),
                f"Wind disperses pollution. Observed concentration on page {n} was 21 micrograms.",
                fontsize=11,
            )
        pdf.save(path)


def test_real_pdf_pages_headings_and_chunk_provenance(tmp_path):
    path = tmp_path / "fixture.pdf"
    fixture_pdf(path)
    pages = parse_pdf(path)
    assert [p.number for p in pages] == [1, 2]
    assert not any(p.is_ocr or p.is_logical for p in pages)
    chunks = chunk_pages(pages, FixtureTokenizer())
    assert {c["page_start"] for c in chunks} == {1, 2}
    assert any(c["section_title"] == "Section 2: Meteorology" for c in chunks)
    assert all(c["page_start"] == c["page_end"] for c in chunks)


def test_token_budget_overlap_and_wide_table_termination():
    text = " ".join(f"word{n}" for n in range(1800))
    chunks = window_chunks([(1, text)], FixtureTokenizer())
    assert all(500 <= c["token_count"] <= 800 for c in chunks)
    assert chunks[0]["text"].split()[-100:] == chunks[1]["text"].split()[:100]
    wide = " ".join(["header"] * 900) + "\n---\n" + text
    table = window_chunks([(2, wide)], FixtureTokenizer(), is_table=True)
    assert len(table) < 10 and all(c["token_count"] <= 800 for c in table)


def test_short_final_boundary_search_does_not_read_past_token_offsets():
    chunks = window_chunks([(1, " ".join(["token"] * 750))], FixtureTokenizer())
    assert len(chunks) == 2
    assert chunks[-1]["text"].split()[-1] == "token"
    assert chunks[0]["text"].split()[-100:] == chunks[1]["text"].split()[:100]


@pytest.mark.django_db
def test_content_idempotence_and_embedding_batch_resume(monkeypatch, tmp_path):
    path = tmp_path / "fixture.md"
    path.write_text("# Weather\n" + " ".join(["wind"] * 6000))
    document = DocumentFactory(
        source_path="fixture.md",
        source_format="markdown",
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    )
    models = Mock()
    models.embed.side_effect = lambda texts: [[1.0] + [0.0] * 1023 for _ in texts]
    with override_settings(BASE_DIR=tmp_path):
        first = ingestion.ingest(document.pk, models=models, source_tokenizer=FixtureTokenizer())
        ids = list(document.chunks.values_list("pk", flat=True))
        count = models.embed.call_count
        again = ingestion.ingest(document.pk, models=models, source_tokenizer=FixtureTokenizer())
        assert first["embedded"] >= 8 and again["status"] == "unchanged"
        assert list(document.chunks.values_list("pk", flat=True)) == ids
        assert models.embed.call_count == count
        document.chunks.filter(pk=ids[-1]).update(embedding=None)
        resumed = ingestion.ingest(document.pk, models=models, source_tokenizer=FixtureTokenizer())
        assert resumed["parsed"] == 0 and resumed["embedded"] == 1
        path.write_text("changed body")
        with pytest.raises(ValueError, match="differs from SHA256"):
            ingestion.ingest(document.pk, models=models, source_tokenizer=FixtureTokenizer())
        assert document.chunks.count() == len(ids)


def test_rrf_deduplicates_each_ranker_and_ties_are_stable():
    order, scores = reciprocal_rank_fusion([[4, 2, 4], [2, 3]])
    assert order == [2, 4, 3]
    assert scores[4] == pytest.approx(1 / 61)
    assert reciprocal_rank_fusion([[3], [2]])[0] == [2, 3]


@pytest.mark.django_db
def test_hybrid_retrieval_and_strict_filters():
    city = CityFactory(slug="delhi")
    doc = DocumentFactory(status=Document.Status.READY, year=2021, category="health")
    a = DocumentChunk.objects.create(
        document=doc,
        chunk_index=0,
        page_start=1,
        page_end=1,
        text="Wind disperses pollution",
        embedding=[1.0] + [0.0] * 1023,
        metadata={"cities": [city.slug]},
    )
    b = DocumentChunk.objects.create(
        document=doc,
        chunk_index=1,
        page_start=2,
        page_end=2,
        text="Pollution damages health",
        embedding=[0.0, 1.0] + [0.0] * 1022,
        metadata={"cities": [city.slug]},
    )
    model = Mock()
    model.embed_query.return_value = [1.0] + [0.0] * 1023
    model.rerank.side_effect = lambda q, texts: [0.9 if "damages" in t else 0.1 for t in texts]
    rows = retrieve("pollution", {"city": "delhi", "year_min": 2020}, models=model)
    assert [r["chunk_id"] for r in rows] == [b.pk, a.pk]
    assert rows[0]["citation"]["page_start"] == 2
    assert retrieve("pollution", {"year_min": 2022}, models=model) == []
    for filters in ({"city": "unknown"}, {"year_min": 2022, "year_max": 2021}, {"sql": "DROP"}):
        with pytest.raises(ValidationError):
            validate_filters(filters)


@pytest.fixture
def tool_data(db, settings):
    city = CityFactory(slug="delhi")
    pollutant = PollutantFactory()
    run = AnalysisRun.objects.create(
        name="phase4",
        status="success",
        started_at=timezone.now(),
        data_start=date(2024, 1, 1),
        data_end=date(2025, 12, 31),
    )
    for name in ["RAG_DATA_RUN", "RAG_NORMALISATION_RUN", "RAG_RESEARCH_RUN"]:
        setattr(settings, name, run.pk)
    CityCoverage.objects.create(
        run=run,
        city=city,
        pollutant=pollutant,
        year=2025,
        hours_present=8760,
        hours_expected=8760,
        valid_days=365,
        expected_days=365,
        valid_months=12,
        eligible=True,
    )
    for day, value in [(1, 60.0), (2, 80.0), (3, None)]:
        CitySeries.objects.create(
            run=run,
            city=city,
            pollutant=pollutant,
            kind="raw",
            frequency="daily",
            date=date(2025, 1, day),
            value=value,
            valid_count=18,
            expected_count=24,
        )
    CitySeries.objects.create(
        run=run,
        city=city,
        pollutant=pollutant,
        kind="raw",
        frequency="monthly",
        date=date(2025, 1, 1),
        value=70,
        valid_count=2,
        expected_count=31,
    )
    CityMetric.objects.create(
        run=run,
        city=city,
        name="ncap",
        result={"cohorts": {"all_stations": {"comparison": {"difference": -4.0}}}},
    )
    CityMetric.objects.create(
        run=run,
        city=city,
        name="rq2",
        result={
            "main_cohort": "all_stations",
            "cohorts": {
                "all_stations": {
                    "explanations": {
                        "shap": [
                            {
                                "season": "winter",
                                "weather": True,
                                "period": "recent",
                                "feature": "wind",
                                "mean_abs_daily_shap": 3.0,
                            }
                        ]
                    }
                }
            },
        },
    )
    return city, run


@pytest.mark.parametrize(
    "name,parameters",
    [
        ("city_annual_mean", {"year": 2025}),
        ("city_monthly_series", {"start": "2025-01-01", "end": "2025-02-01"}),
        ("exceedance_days", {"year": 2025, "threshold": 60}),
        ("ncap_proxy_comparison", {}),
        ("rq2_drivers", {"season": "winter"}),
        ("latest_forecast", {}),
        ("forecast_skill", {"horizon": 1}),
        ("data_coverage", {}),
    ],
)
def test_all_eight_tools_validate_and_return_real_provenance(tool_data, name, parameters):
    city, run = tool_data
    result = call_tool(name, {"city": city.slug, **parameters})
    assert result["citation"]["analysis_run"] == run.pk
    assert result["citation"]["query_parameters"] == result["parameters"]
    assert result["citation"]["url"].startswith("/api/")
    if name == "city_annual_mean":
        assert result["values"]["annual_mean"] == 70
    if name == "exceedance_days":
        assert result["values"]["days_above_threshold"] == 1
    for invalid in ["unknown", "delhi'; DROP TABLE warehouse_city;--"]:
        with pytest.raises(ValidationError):
            call_tool(name, {"city": invalid, **parameters})
    with pytest.raises(ValidationError):
        call_tool(name, {"city": city.slug, "sql": "SELECT 1", **parameters})


@pytest.mark.parametrize(
    "name,parameters",
    [
        ("city_annual_mean", {"year": True}),
        ("city_monthly_series", {"start": "2025-02-01", "end": "2025-01-01"}),
        ("exceedance_days", {"year": 2025, "threshold": float("nan")}),
        ("rq2_drivers", {"season": "autumn"}),
        ("forecast_skill", {"horizon": 4}),
        ("forecast_skill", {"horizon": True}),
    ],
)
def test_tool_ranges_and_nonfinite_values_rejected(tool_data, name, parameters):
    with pytest.raises(ValidationError):
        call_tool(name, {"city": "delhi", **parameters})
    with pytest.raises(ValidationError):
        call_tool("raw_sql", {"city": "delhi"})


def test_number_and_sentence_verification_removes_unsupported_claims():
    evidence = [
        {
            "alias": "E1",
            "text": "Wind speed was 4.2 metres per second.",
            "citation": {"id": "chunk:1", "label": "Report, p. 2"},
        }
    ]
    answer, citations, check = verify_answer(
        "Wind speed was 4.2 metres per second. [E1]\n"
        "Wind speed was 99 metres per second. [E1]\n"
        "Factories caused 4.2 deaths. [E1]\nA claim. [E9]",
        evidence,
    )
    assert "99" not in answer and "Factories" not in answer
    assert len(citations) == 1 and check["supported_claims"] == 1
    assert {r["reason"] for r in check["removed"]} == {
        "unsupported_number",
        "sentence_not_supported_verbatim",
        "citation_not_in_evidence",
    }


def test_no_key_provider_and_mocked_openai_responses(monkeypatch):
    for key in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "OLLAMA_MODEL", "LLM_PROVIDER"]:
        monkeypatch.delenv(key, raising=False)
    assert choose_provider().name == "extractive"
    monkeypatch.setenv("OPENAI_API_KEY", "fixture")
    monkeypatch.setenv("OPENAI_MODEL", "fixture-model")
    response = Mock()
    response.json.return_value = {
        "output": [
            {
                "type": "message",
                "content": [{"type": "output_text", "text": "Supported passage. [E1]"}],
            }
        ]
    }
    post = Mock(return_value=response)
    monkeypatch.setattr("apps.rag.providers.requests.post", post)
    assert Provider("openai", "fixture-model").generate("question", []) == "Supported passage. [E1]"
    assert post.call_args.kwargs["json"]["store"] is False


@pytest.mark.django_db
def test_refusal_persistence_and_source_page_api(api_client, monkeypatch):
    monkeypatch.setattr(service, "route_question", lambda q: ("literature", []))
    result = service.ask(
        "What is the exact result of an unknown experiment?", retrieval=lambda *a: []
    )
    assert result["answer"] == REFUSAL and result["citations"] == []
    assert Query.objects.get(pk=result["query_id"]).verification["refused"]
    doc = DocumentFactory()
    DocumentPage.objects.create(document=doc, page_number=2, text="Original source page")
    assert (
        api_client.get(f"/api/rag/documents/{doc.pk}/page/2/").data["text"]
        == "Original source page"
    )
    assert api_client.get(f"/api/rag/documents/{doc.pk}/page/99/").status_code == 404
    assert api_client.post("/api/rag/ask/", {"question": ""}, format="json").status_code == 400
    assert api_client.get("/ask/").status_code == 200


@pytest.mark.django_db
def test_no_keys_produces_a_cited_extractive_answer(monkeypatch):
    for key in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "OLLAMA_MODEL", "LLM_PROVIDER"]:
        monkeypatch.delenv(key, raising=False)
    passage = {
        "chunk_id": 123,
        "text": "Wind disperses pollution in the atmospheric boundary layer.",
        "citation": {"id": "chunk:123", "kind": "document", "label": "Fixture, p. 2"},
        "rerank_score": 0.9,
    }
    result = service.ask("How does wind disperse pollution?", retrieval=lambda *a: [passage])
    assert result["provider"] == "extractive" and result["answer"] != REFUSAL
    assert "[Fixture, p. 2]" in result["answer"]
    assert Query.objects.get(pk=result["query_id"]).retrieved_ids == [123]


def test_a_secondary_irrelevant_citation_cannot_support_a_claim():
    evidence = [
        {
            "alias": "E1",
            "text": "Wind speed was 4.2 metres per second.",
            "citation": {"id": "chunk:1", "label": "Report, p. 1"},
        },
        {
            "alias": "E2",
            "text": "Temperature was 4.2 degrees Celsius.",
            "citation": {"id": "chunk:2", "label": "Report, p. 2"},
        },
    ]
    answer, _, check = verify_answer("Wind speed was 4.2 metres per second. [E1] [E2]", evidence)
    assert answer == REFUSAL
    assert check["removed"][0]["reason"] == "sentence_not_supported_verbatim"


@pytest.mark.django_db
def test_pdf_admin_upload_computes_identity_and_queues_ingestion(
    tmp_path, monkeypatch, django_capture_on_commit_callbacks
):
    from django.contrib import admin
    from django.core.files.uploadedfile import SimpleUploadedFile

    from apps.rag.admin import DocumentAdmin
    from apps.rag.forms import DocumentForm

    path = tmp_path / "upload.pdf"
    fixture_pdf(path)
    body = path.read_bytes()
    delayed = Mock()
    monkeypatch.setattr("apps.rag.tasks.ingest_document.delay", delayed)
    form = DocumentForm(
        data={"title": "Uploaded fixture", "category": "methods"},
        files={"file": SimpleUploadedFile("upload.pdf", body, content_type="application/pdf")},
    )
    assert form.is_valid(), form.errors
    document = form.save(commit=False)
    with override_settings(MEDIA_ROOT=tmp_path / "media"):
        with django_capture_on_commit_callbacks(execute=True):
            DocumentAdmin(Document, admin.site).save_model(None, document, form, False)
    assert document.sha256 == hashlib.sha256(body).hexdigest()
    assert document.size_bytes == len(body)
    delayed.assert_called_once_with(document.pk)


@pytest.mark.django_db
def test_nested_ask_filters_and_explain_context_validation(api_client, monkeypatch):
    CityFactory(slug="delhi")
    monkeypatch.setattr(service, "retrieve", lambda *a, **kw: [])
    response = api_client.post(
        "/api/rag/ask/",
        {
            "question": "What does wind do?",
            "filters": {"city": "delhi", "year_min": 2020},
        },
        format="json",
    )
    assert response.status_code == 200 and response.data["answer"] == REFUSAL
    bad = api_client.post(
        "/api/rag/ask/",
        {
            "question": "Wind",
            "filters": {"sql": "SELECT 1"},
        },
        format="json",
    )
    assert bad.status_code == 400
    for payload in [
        {"city": "unknown"},
        {"city": "delhi", "horizon": True},
        {"city": "delhi", "start": "2025-02-01", "end": "2025-01-01"},
    ]:
        response = api_client.post(
            "/api/rag/explain/",
            {
                "context_type": "forecast",
                "payload": payload,
            },
            format="json",
        )
        assert response.status_code == 400


def test_embedding_cache_deduplicates_text_and_separates_precision(tmp_path, monkeypatch):
    from apps.rag.encoders import CPUModels

    model = CPUModels()
    request = Mock(return_value={"vectors": [[1.0] + [0.0] * 1023]})
    monkeypatch.setattr(model, "request", request)
    monkeypatch.setenv("RAG_MODEL_DTYPE", "float32")
    with override_settings(BASE_DIR=tmp_path):
        vectors = model.embed(["Same passage", "Same passage"])
        assert vectors[0] == vectors[1]
        assert request.call_args.args[1]["texts"] == ["Same passage"]
        assert model.embed(["Same passage"]) == [vectors[0]]
        assert request.call_count == 1
        monkeypatch.setenv("RAG_MODEL_DTYPE", "float16")
        model.embed(["Same passage"])
        assert request.call_count == 2


@pytest.mark.django_db
def test_resume_after_last_saved_batch_repairs_ready_status(tmp_path):
    path = tmp_path / "fixture.md"
    path.write_text("# Meteorology\nWind disperses atmospheric pollutants.")
    document = DocumentFactory(
        source_path="fixture.md",
        source_format="markdown",
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    )
    model = Mock()
    model.embed.side_effect = lambda texts: [[1.0] + [0.0] * 1023 for _ in texts]
    with override_settings(BASE_DIR=tmp_path):
        ingestion.ingest(document.pk, models=model, source_tokenizer=FixtureTokenizer())
        Document.objects.filter(pk=document.pk).update(status="embedding")
        model.reset_mock()
        result = ingestion.ingest(document.pk, models=model, source_tokenizer=FixtureTokenizer())
    document.refresh_from_db()
    assert result["embedded"] == 0 and document.status == "ready"
    model.embed.assert_not_called()


@pytest.mark.django_db
def test_explicit_snapshot_citation_resolves_without_changing_analysis_default(api_client):
    city = CityFactory(slug="delhi")
    pollutant = PollutantFactory()
    full = AnalysisRun.objects.create(
        name="phase3a2",
        status="success",
        started_at=timezone.now(),
        data_start=date(2025, 1, 1),
        data_end=date(2025, 12, 31),
    )
    snapshot = AnalysisRun.objects.create(
        name="phase3b-data",
        status="success",
        started_at=timezone.now(),
        data_start=date(2025, 1, 1),
        data_end=date(2025, 12, 31),
    )
    for run, value in [(full, 17), (snapshot, 23)]:
        CitySeries.objects.create(
            run=run,
            city=city,
            pollutant=pollutant,
            kind="raw",
            frequency="daily",
            date=date(2025, 1, 1),
            value=value,
            valid_count=24,
            expected_count=24,
        )
    url = "/api/analytics/city/delhi/series/"
    assert api_client.get(url).data["results"][0]["run"] == full.pk
    response = api_client.get(url, {"run": snapshot.pk})
    assert response.status_code == 200 and response.data["results"][0]["value"] == 23
    snapshot.status = "failed"
    snapshot.save(update_fields=["status"])
    assert api_client.get(url, {"run": snapshot.pk}).status_code == 404


def test_numeric_evaluation_scores_values_by_field_and_tracks_missing_data():
    from apps.rag.evaluation import numeric_cells, score_data_answer

    record = {
        "data_available": True,
        "expected_numeric_cells": numeric_cells(
            [
                "| year | 2025 |",
                "| annual_mean | 44.25 |",
                "| units | µg/m³ |",
            ]
        ),
    }
    correct = score_data_answer(
        record,
        {
            "answer": "| year | 2025.0 | [source] |\n| annual_mean | 44.250 | [source] |",
        },
    )
    assert correct["expected_numeric_values"] == 2
    assert correct["correct_numeric_values"] == 2 and correct["exact_numeric_cells"] == 2
    wrong = score_data_answer(
        record,
        {
            "answer": "| year | 44.25 |\n| annual_mean | 2025 |",
        },
    )
    assert wrong["correct_numeric_values"] == 0 and wrong["extra_numeric_values"] == 2
    unavailable = score_data_answer({**record, "data_available": False}, {"answer": REFUSAL})
    assert unavailable["expected_numeric_values"] == 0
    assert unavailable["correct_missing_data_refusal"]


@pytest.mark.django_db
def test_absent_analysis_run_refuses_instead_of_server_error(settings):
    CityFactory(slug="delhi")
    settings.RAG_DATA_RUN = 999999
    result = service.ask("What was the annual mean PM2.5 in Delhi in 2025?")
    assert result["answer"] == REFUSAL
    assert result["verification"]["tool_errors"]


def test_one_column_paragraph_is_not_converted_to_a_table(tmp_path):
    import pymupdf

    path = tmp_path / "paragraph.pdf"
    with pymupdf.open() as pdf:
        page = pdf.new_page()
        page.insert_text((50, 50), "Chemistry", fontsize=20)
        for y in (80, 110, 140, 170):
            page.draw_line((40, y), (550, y))
        for x in (40, 550):
            page.draw_line((x, 80), (x, 170))
        page.insert_text((50, 100), "Secondary particles form from SO2, NOx and NH3.", fontsize=11)
        page.insert_text(
            (50, 130), "The sources include road dust and airborne flyash.", fontsize=11
        )
        pdf.save(path)
    pages = parse_pdf(path)
    assert not pages[0].tables
    assert any("SO2, NOx and NH3" in s["text"] for s in pages[0].sections)


def test_scientific_interval_brackets_are_preserved_as_source_text():
    sentence = "The estimated burden was 0.98 million deaths [0.77–1.19]."
    evidence = [
        {
            "alias": "E1",
            "text": sentence,
            "citation": {"id": "chunk:1", "label": "Fixture report, p. 1"},
        }
    ]
    answer, citations, checks = verify_answer(sentence + " [E1]", evidence)
    assert sentence in answer and len(citations) == 1
    assert not checks["removed"]
    rejected, _, _ = verify_answer(sentence + " [Invented report, p. 99]", evidence)
    assert rejected == REFUSAL
