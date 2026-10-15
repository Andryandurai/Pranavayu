"""Audit regressions; the original Phase 1–6A tests remain unchanged."""

from django.contrib import admin

from apps.ingest.models import DataSource, RawAsset
from apps.rag.forms import DocumentForm
from apps.rag.management.commands.audit_reranker import scored_subset
from apps.vayusim.presets import presets
from apps.vayusim.service import interpretation


def test_cutoff_can_improve_recall_by_removing_high_scoring_non_gold_candidates():
    candidates = [{"chunk_id": i} for i in range(1, 41)]
    scores = [0.0] * 40
    scores[0] = 0.8
    scores[24:] = [0.9] * 16
    # The same gold pair score is used in both subsets; no model or ties changed.
    assert scored_subset(candidates, scores, {1}, 24)["recall_at_10"] == 1
    assert scored_subset(candidates, scores, {1}, 40)["recall_at_10"] == 0


def test_reranker_audit_breaks_score_ties_by_stable_chunk_id():
    candidates = [{"chunk_id": i} for i in range(40, 0, -1)]
    result = scored_subset(candidates, [0.5] * 40, {1}, 40)
    assert result["ids"] == list(range(1, 41))
    assert result["mrr"] == 1


def test_road_dust_citation_has_direct_source_page_and_no_emission_default():
    preset = next(p for p in presets() if p["id"] == "highway")
    assert preset["name"] == "Road dust resuspension"
    assert preset["defaults"]["emission_gs"] is None
    assert "emission_gs" in preset["required_parameters"]
    assert preset["citations"][0]["url"].endswith("13.2.1_paved_roads.pdf")
    assert "13.2.1-1" in preset["citations"][0]["pages"]
    assert "Exhaust, brake wear and tire wear are excluded" in preset["note"]


def test_source_labels_use_explicit_assumptions_and_preserve_population_scope():
    result = interpretation(
        {"sources": [{"emission_gs": 1.0, "assumptions": "Declared hypothetical release"}]}
    )
    assert result["sources"][0]["label"] == "hypothetical 1 g/s source"
    assert "footprint only" in result["population_scope"]
    assert "does not scale linearly" in result["scaling"]


def test_unit_emission_alone_does_not_label_a_real_source_as_hypothetical():
    result = interpretation({"sources": [{"emission_gs": 1.0}]})
    assert result["sources"][0]["label"] == "user-specified 1 g/s source"
    result = interpretation(
        {"sources": [{"emission_gs": 1.0, "assumptions": "This is not a hypothetical source"}]}
    )
    assert result["sources"][0]["label"] == "user-specified 1 g/s source"


def test_source_url_form_chooses_https_and_preserves_explicit_http_and_model_metadata():
    field = DocumentForm.base_fields["source_url"]
    assert field.clean("example.org/report") == "https://example.org/report"
    assert field.clean("http://example.org/report") == "http://example.org/report"
    assert field.max_length == 1000
    assert field.required is False


def test_ingestion_admin_url_forms_choose_https_without_transitional_settings():
    for model, name in [(DataSource, "url"), (RawAsset, "download_url")]:
        field = admin.site._registry[model].formfield_for_dbfield(
            model._meta.get_field(name), request=None
        )
        assert field.clean("example.org/source") == "https://example.org/source"
