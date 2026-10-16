"""External printed values and equation coverage; no expected engine-generated sigmas."""

import json
from pathlib import Path

import pytest

from apps.vayusim.physics.dispersion import COEFFICIENTS, sigmas

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures/vayusim-independent-references.json").read_text()
)


@pytest.mark.parametrize("axis", ["y", "z"])
def test_independently_printed_doe_rural_d_1000m(axis):
    """DOE-HDBK-1224-2018 p.213 (PDF p.228), after Eq.6-10: 76.3/37.9 m."""
    case = FIXTURE["numeric_cases"][0]
    actual = sigmas(case["x_m"], case["stability"], case["environment"])[axis == "z"]
    assert actual == pytest.approx(
        case[f"sigma_{axis}_m"], rel=FIXTURE["tolerances"]["printed_sigma_relative"]
    )


@pytest.mark.parametrize("stability", list("ABCDEF"))
def test_urban_branch_equation_matches_epa_table(stability):
    """ISC3 Vol II p.1-19 Tables1-3/1-4; equation coverage, not numeric validation."""
    published = FIXTURE["urban_equation_transcription"]["rows"][stability]
    assert COEFFICIENTS["urban"][stability] == tuple(published)
