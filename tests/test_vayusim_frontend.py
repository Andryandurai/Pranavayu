"""Offline Phase 6B contracts; all fields originate in actual synthetic stored runs."""

import copy
import io
import json
from unittest.mock import patch

import numpy as np
import pytest
from PIL import Image

from apps.vayusim.models import ScenarioRun
from apps.vayusim.service import run_response
from tests import test_vayusim_api
from tests.factories import CityFactory

inputs = test_vayusim_api.inputs


def submit(client, inputs, settings, tmp_path):
    settings.BASE_DIR = tmp_path
    response = client.post("/api/vayusim/run/", inputs, content_type="application/json")
    assert response.status_code == 200, response.content
    return response.json()


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("environment", "stability", "expected"),
    [
        ("urban", "C", "unvalidated_branch"),
        ("urban", "F", "unvalidated_branch"),
        ("urban", "D", "formula_check_only"),
        ("rural", "C", "formula_check_only"),
        ("rural", "F", "formula_check_only"),
    ],
)
def test_status_on_run_scenario_header_and_export(
    client, inputs, settings, tmp_path, environment, stability, expected
):
    inputs["environment"] = environment
    run_data = submit(client, inputs, settings, tmp_path)
    run = ScenarioRun.objects.get(pk=run_data["run_id"])
    run.stability_class = stability
    run.save(update_fields=["stability_class"])
    before = copy.deepcopy(run.summary)
    # Mutable scenario must not control the retained run's disclosure.
    run.scenario.inputs["environment"] = "rural" if environment == "urban" else "urban"
    run.scenario.save(update_fields=["inputs"])
    detail = client.get(f"/api/vayusim/runs/{run.pk}/").json()
    assert detail["validation_status"] == expected
    assert detail["summary"] == {k: v for k, v in before.items() if k != "contours"}
    assert client.get(detail["grid_header_url"]).json()["validation_status"] == expected
    shared = client.get(f"/api/vayusim/scenarios/{run.scenario.share_slug}/").json()
    assert shared["validation_status"] == shared["runs"][0]["validation_status"] == expected
    page = client.get(f"/vayusim/?run={run.pk}").content.decode()
    snapshot = json.loads(
        page.split('id="vayu-initial" type="application/json">')[1].split("</script>")[0]
    )
    assert snapshot["inputs"]["environment"] == environment
    image_response = client.get(detail["export_url"])
    assert image_response.status_code == 200
    image = Image.open(io.BytesIO(image_response.content))
    assert image.info["validation_status"] == expected
    assert expected.replace("_", " ").upper() in image.info["Description"]
    # Annotation occupies actual image pixels as well as PNG metadata.
    pixels = np.asarray(image)
    assert np.unique(pixels[40:68, 24:800].reshape(-1, 3), axis=0).shape[0] > 10
    run.refresh_from_db()
    assert run.summary == before


@pytest.mark.django_db
def test_vertical_grid_is_stored_idempotent_and_get_never_computes(
    client, inputs, settings, tmp_path
):
    value = submit(client, inputs, settings, tmp_path)
    url = value["section_url"]
    assert client.get(url).status_code == 404
    response = client.post(url, {}, content_type="application/json")
    assert response.status_code == 200
    section = response.json()
    assert section["inputs_hash"] == value["inputs_hash"]
    assert section["validation_status"] == value["validation_status"]
    assert len(section["values_ugm3"]) == len(section["height_m"])
    assert len(section["values_ugm3"][0]) == len(section["distance_m"])
    assert np.max(section["values_ugm3"]) > 0
    with patch(
        "apps.vayusim.presentation.simulate", side_effect=AssertionError("must read stored grid")
    ):
        assert client.get(url).json() == section
        assert client.post(url, {}, content_type="application/json").json() == section
    run = ScenarioRun.objects.get(pk=value["run_id"])
    assert run_response(run)["summary"] == value["summary"]


@pytest.mark.django_db
def test_all_example_labels_and_shared_link_render_without_scripts(
    client, inputs, settings, tmp_path
):
    value = submit(client, inputs, settings, tmp_path)
    first = ScenarioRun.objects.get(pk=value["run_id"])
    runs = [first]
    for index, (name, stability) in enumerate(
        [("Delhi", "C"), ("Mumbai", "C"), ("Hyderabad", "F")]
    ):
        if index:
            cloned = copy.deepcopy(inputs)
            CityFactory(slug=name.lower(), name=name)
            cloned["city"] = name.lower()
            cloned["sources"][0]["emission_gs"] += index
            created = submit(client, cloned, settings, tmp_path)
            runs.append(ScenarioRun.objects.get(pk=created["run_id"]))
        run = runs[-1]
        run.stability_class = stability
        run.save(update_fields=["stability_class"])
        run.scenario.city.name = name
        run.scenario.city.save(update_fields=["name"])
    with patch("apps.vayusim.views.EXAMPLE_HASHES", tuple(r.inputs_hash for r in runs)):
        for route in [
            "/vayusim/",
            "/simulator/",
            f"/vayusim/?scenario={first.scenario.share_slug}",
        ]:
            page = client.get(route)
            assert page.status_code == 200
            html = page.content.decode()
            assert html.count("unvalidated branch") >= 6
            assert 'id="timeline"' in html and 'id="section-canvas"' in html
            assert 'src="https://' not in html  # scripts and fonts are local
            assert 'id="summary-validation"' in html and "measured total (all sources)" in html
            assert all(f'data-run="{r.pk}"' in html for r in runs)
            assert all(name in html for name in ["Delhi", "Mumbai", "Hyderabad"])
        assert client.get("/vayusim/?run=bad").status_code == 404
        assert client.get("/vayusim/?scenario=missing").status_code == 404


@pytest.mark.django_db
def test_day_cache_keeps_ids_labels_and_numeric_summaries(client, inputs, settings, tmp_path):
    settings.BASE_DIR = tmp_path
    from datetime import datetime

    from apps.vayusim.weather import weather_for
    from apps.warehouse.models import City

    inputs["datetime"] = datetime.fromisoformat(inputs["datetime"])
    weather, proof, flags = weather_for(inputs, City.objects.get(slug=inputs["city"]))
    inputs.pop("weather")
    inputs["weather_mode"] = "real"
    body = json.loads(json.dumps(inputs, default=str))
    with patch("apps.vayusim.service.weather_for", return_value=(weather, proof, flags)):
        first = client.post("/api/vayusim/day/", body, content_type="application/json").json()
        second = client.post("/api/vayusim/day/", body, content_type="application/json").json()
    assert len(first["hours"]) == 24 and ScenarioRun.objects.count() == 24
    assert all(h["available"] and h["cached"] for h in second["hours"])
    for a, b in zip(first["hours"], second["hours"], strict=True):
        assert a["run_id"] == b["run_id"] and a["summary"] == b["summary"]
        assert a["validation_status"] == b["validation_status"] == "unvalidated_branch"


@pytest.mark.django_db
def test_source_removed_comparison_uses_a_second_stored_zero_field(
    client, inputs, settings, tmp_path
):
    first = submit(client, inputs, settings, tmp_path)
    inputs["sources"][0]["emission_gs"] = 0
    second = submit(client, inputs, settings, tmp_path)
    assert first["run_id"] != second["run_id"] and ScenarioRun.objects.count() == 2
    assert first["summary"]["weather"] == second["summary"]["weather"]
    assert second["summary"]["peak_ugm3"] == 0
    content = client.get(second["grid_url"])
    assert not np.frombuffer(b"".join(content.streaming_content), dtype="<f4").any()


@pytest.mark.django_db
def test_new_artifact_routes_unknown_run(client):
    assert client.get("/api/vayusim/runs/999999/export.png").status_code == 404
    assert client.get("/api/vayusim/runs/999999/section/").status_code == 404
    assert (
        client.post(
            "/api/vayusim/runs/999999/section/", {}, content_type="application/json"
        ).status_code
        == 404
    )


@pytest.mark.django_db
def test_scenario_without_runs_has_no_branch_claim(client, inputs, settings, tmp_path):
    value = submit(client, inputs, settings, tmp_path)
    run = ScenarioRun.objects.get(pk=value["run_id"])
    slug = run.scenario.share_slug
    run.delete()
    response = client.get(f"/api/vayusim/scenarios/{slug}/")
    assert response.status_code == 200
    assert response.json()["runs"] == [] and response.json()["validation_status"] is None
