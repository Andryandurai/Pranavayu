import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.analytics.models import AnalysisRun, CityMetric
from tests.factories import CityFactory


@pytest.mark.django_db
def test_ncap_is_a_read_only_proxy_and_failed_runs_are_not_published():
    city = CityFactory()
    fields = dict(
        name="phase3b", data_start="2015-01-01", data_end="2025-12-31", started_at=timezone.now()
    )
    run = AnalysisRun.objects.create(status="success", **fields)
    AnalysisRun.objects.create(status="failed", **fields)
    CityMetric.objects.create(
        run=run,
        city=city,
        name="ncap",
        result={
            "label": "PM2.5 proxy for NCAP progress",
            "is_official_compliance_result": False,
            "official_compliance_assessment": "not assessed",
            "cohorts": {},
        },
    )
    CityMetric.objects.create(run=run, city=city, name="rq2", result={"scope": "fixed panel only"})
    client = APIClient()
    response = client.get("/api/analytics/ncap/")
    assert response.status_code == 200
    assert response.data["run"] == run.pk
    assert response.data["label"] == "PM2.5 proxy for NCAP progress"
    assert response.data["is_official_compliance_result"] is False
    assert response.data["official_compliance_assessment"] == "not assessed"
    assert response.data["results"][0]["result"]["is_official_compliance_result"] is False
    assert client.post("/api/analytics/ncap/", {}).status_code == 405
    assert client.get("/api/analytics/ncap/?run=bad").status_code == 400
    assert client.get(f"/api/analytics/rq2/{city.slug}/").status_code == 200
    assert client.get("/api/analytics/comparisons/").data["is_official_compliance_result"] is False
