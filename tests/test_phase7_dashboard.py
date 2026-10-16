import json
from pathlib import Path

import pytest

from apps.dashboard import evidence


@pytest.mark.django_db
def test_dashboard_is_stored_only_and_exposes_limits(client, django_assert_num_queries):
    with django_assert_num_queries(0):
        response = client.get("/dashboard/")
    assert response.status_code == 200
    html = response.content.decode()
    for text in [
        "17,504,928",
        "16,266,240",
        "1,238,688",
        "-17.59",
        "-35.07",
        "+1.66",
        "unvalidated branch",
        "hypothetical 1 g/s source",
        "7194",
        "80.31",
        "0.6933",
    ]:
        assert text in html.replace("7,194", "7194")
    assert html.count("coverage-fail") == 14
    assert html.count("Persistence advised") == 9
    assert "Automatic fallback for all nine is not implemented" in html
    assert "5 still use other algorithms" in html
    assert "Extractive retrieval with verified citations" in html
    assert "local LLM is opt-in and failed its quality gate" in html
    assert 'src="https://' not in html
    for section in ["ingestion", "analytics", "forecasting", "assistant", "dispersion", "testing"]:
        assert f'id="{section}"' in html


@pytest.mark.parametrize("key", ["snapshot", "phase3b", "phase4", "phase5", "phase6a", "examples"])
def test_evidence_serves_exact_allowed_file(client, key):
    response = client.get(f"/evidence/{key}/")
    assert response.status_code == 200
    assert (
        b"".join(response.streaming_content) == (evidence.ROOT / evidence.SOURCES[key]).read_bytes()
    )
    assert response["Content-Type"].startswith("text/plain")
    assert response["X-Content-Type-Options"] == "nosniff"


@pytest.mark.parametrize(
    "path", ["/evidence/env/", "/evidence/secret/", "/evidence/.env/", "/evidence/..%2F.env/"]
)
def test_evidence_cannot_read_arbitrary_files(client, path):
    assert client.get(path).status_code == 404


def test_missing_snapshot_has_no_invented_values(client, monkeypatch, tmp_path):
    monkeypatch.setattr(evidence, "ROOT", tmp_path)
    result = client.get("/dashboard/")
    assert result.status_code == 503
    assert b"Stored dashboard snapshot unavailable" in result.content
    assert b"17,504,928" not in result.content
    assert client.get("/evidence/snapshot/").status_code == 404


def test_snapshot_consistency_and_no_result_reselection():
    data = json.loads((evidence.ROOT / evidence.SOURCES["snapshot"]).read_text(encoding="utf-8"))
    assert data["combined_observation_rows"] == (
        data["ingestion"]["readings_total"]
        + data["ingestion"]["weather"]["rows"]
        + data["ingestion"]["fires"]["rows"]
    )
    assert (
        sum(row["rows"] for row in data["ingestion"]["quality_flags"])
        == data["ingestion"]["readings_total"]
    )
    assert sum(row["persistence_advised"] for row in data["forecasts"]) == 9
    assert len(data["forecasts"]) == 21
    assert all(
        "prediction" in row["models"] and "persistence" in row["models"]
        for row in data["forecasts"]
    )
    assert data["fallback_gap_count"] == 5
    original = json.loads(
        (Path(__file__).resolve().parents[1] / "docs/results/PHASE6B_METRICS.json").read_text(
            encoding="utf-8"
        )
    )
    assert data["examples"] == original["preservation"]["examples"]
