"""Reference correction and explicit provider opt-in regressions."""

import json
from pathlib import Path

import pytest

from apps.rag.providers import choose_provider
from apps.vayusim.physics.dispersion import sigmas


def test_brune_rural_b_uses_table_equation_in_metres():
    """Brune METEO532 §2.2.5 Table 2.3, rural B (unpaginated).

    https://personal.ems.psu.edu/~brune/m532/m532_theatmosphere.htm
    The following paragraph's 210 m is excluded, not a new fitting target.
    """
    fixture = json.loads(
        (Path(__file__).parent / "fixtures/vayusim-textbook-audit.json").read_text()
    )["brune"]
    assert fixture["x_units"] == "m"
    assert fixture["table_derived_sigma_y_m"] == pytest.approx(152.55401427929476, rel=1e-12)
    assert sigmas(fixture["x_m"], "B", "rural") == pytest.approx(
        (152.55401427929476, 120.0), rel=1e-12
    )
    assert sigmas(fixture["x_m"], "B", "urban") == pytest.approx(
        (270.4493615131253, 339.4112549695428), rel=1e-12
    )
    assert not fixture["excluded_paragraph_diagnostic"]["included_in_validation_pass_count"]


def test_unset_provider_remains_extractive_with_generation_configured(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "synthetic-test-key")
    monkeypatch.setenv("ANTHROPIC_MODEL", "synthetic-test-model")
    monkeypatch.setenv("OLLAMA_ENABLED", "true")
    monkeypatch.setenv("OLLAMA_MODEL", "synthetic-test-model")
    assert choose_provider().name == "extractive"


def test_ollama_remains_available_only_when_opted_in(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_MODEL", "synthetic-test-model")
    monkeypatch.setenv("OLLAMA_ENABLED", "false")
    assert choose_provider().name == "extractive"
    monkeypatch.setenv("OLLAMA_ENABLED", "true")
    assert choose_provider().name == "ollama"
