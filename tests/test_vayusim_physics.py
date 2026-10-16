"""Physics checks run entirely offline; fixtures are not warehouse observations."""

import json
from pathlib import Path

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from apps.vayusim.physics import concentration, expand_sources, simulate
from apps.vayusim.physics.dispersion import sigmas
from apps.vayusim.physics.meteorology import stability_class, wind_at_height
from apps.vayusim.physics.rise import effective_height

POSITIVE = st.floats(min_value=1, max_value=1000, allow_nan=False, allow_infinity=False)
WEATHER = {
    "wind_speed_ms": 4.0,
    "wind_direction_deg": 270.0,
    "temperature_k": 293.0,
    "stability_class": "D",
    "mixing_height_m": None,
}
SOURCE = {
    "type": "point",
    "east_m": 0.0,
    "north_m": 0.0,
    "emission_gs": 10.0,
    "height_m": 0.0,
    "diameter_m": 0.0,
    "exit_velocity_ms": 0.0,
    "exit_temperature_k": 293.0,
}


def test_turner_problem9_concentrations():
    """Turner AP26 (1970), Chapter7 Problem9, Table7-4.

    EPA copy https://nepis.epa.gov/Exe/ZyPURL.cgi?Dockey=9101GKEZ.TXT
    Q=151g/s, u=4m/s, H=150m, x=1km, chart sy=157m, sz=110m.
    Tests the Gaussian equation using published chart inputs, NOT substituting
    Briggs for the workbook's different Pasquill chart parameterisation.
    This EPA HTML transcription is unpaginated. The separately checked Cimbala
    PDF example below provides the required exact-page worked example.
    """
    actual = concentration(
        151.0, 4.0, 157.0, 110.0, 0.0, z=np.array([0.0, 30.0, 150.0]), height=150.0
    )
    np.testing.assert_allclose(actual, [278.0, 285.0, 358.0], rtol=0.10)


def test_cimbala_reflecting_ground_worked_example():
    """J.M.Cimbala, PSU ME433 Lesson06E, PDF p3 worked example (incl handwritten solution).

    https://www.me.psu.edu/cimbala/me433/Lesson_Notes/ME433_Lesson_06_E_Reflecting_Ground.pdf
    At4.85km: Q=110kg/s, u=5m/s, H=80+20=100m,
    published Martin-model sy=278.97m, sz=87.51m, reflected C=149.3mg/m³.
    Primitive validation uses those published sigmas; Briggs is checked separately.
    """
    value = concentration(110000.0, 5.0, 278.97, 87.51, 0.0, z=0.0, height=100.0)
    assert value / 1000 == pytest.approx(149.3, rel=0.10)


@pytest.mark.parametrize(
    "environment,stability,expected",
    [
        ("rural", "A", (209.762, 200.0)),
        ("rural", "B", (152.554, 120.0)),
        ("rural", "D", (76.277, 37.947)),
        ("rural", "F", (38.139, 12.308)),
        ("urban", "A", (270.449, 339.411)),
        ("urban", "D", (135.225, 122.788)),
        ("urban", "F", (92.967, 50.596)),
    ],
)
def test_briggs_published_table(environment, stability, expected):
    """Brune, PSU METEO532 Table2.3 (unpaginated), independent table arithmetic at1km.

    This is coefficient transcription validation, not a chart/worked-example sigma claim.
    https://personal.ems.psu.edu/~brune/m532/m532_theatmosphere.htm
    """
    np.testing.assert_allclose(sigmas(1000.0, stability, environment), expected, rtol=0.05)


@given(q=POSITIVE, sy=POSITIVE, sz=POSITIVE, wind=st.floats(1, 20))
@settings(max_examples=30, deadline=1000)
def test_crosswind_mass_reflection(q, sy, sz, wind):
    y = np.linspace(-10 * sy, 10 * sy, 2001)
    integrated = np.trapezoid(concentration(q, wind, sy, sz, y, z=0.0, height=0.0), y)
    assert integrated == pytest.approx(2 * q * 1e6 / (np.sqrt(2 * np.pi) * wind * sz), rel=1e-6)


@given(y=st.floats(-5000, 5000), sy=POSITIVE, sz=POSITIVE)
def test_crosswind_symmetry(y, sy, sz):
    assert concentration(10.0, 4.0, sy, sz, y) == concentration(10.0, 4.0, sy, sz, -y)


@given(q=POSITIVE, factor=st.floats(0.1, 10), sy=POSITIVE, sz=POSITIVE)
def test_emission_linearity(q, factor, sy, sz):
    assert concentration(q * factor, 4.0, sy, sz, 5.0) == pytest.approx(
        factor * concentration(q, 4.0, sy, sz, 5.0), rel=1e-12
    )


@given(q1=POSITIVE, q2=POSITIVE, shift=st.floats(-100, 100))
@settings(max_examples=30)
def test_source_superposition(q1, q2, shift):
    east, north = np.meshgrid(np.linspace(100, 5000, 20), np.linspace(-1000, 1000, 20))
    a, b = {**SOURCE, "emission_gs": q1}, {**SOURCE, "emission_gs": q2, "north_m": shift}
    combined, _ = simulate(east, north, [a, b], WEATHER)
    first, _ = simulate(east, north, [a], WEATHER)
    second, _ = simulate(east, north, [b], WEATHER)
    np.testing.assert_allclose(combined, first + second, rtol=2e-6, atol=1e-8)


@given(height=st.floats(0, 500), extra=st.floats(0, 500))
def test_higher_release_cannot_raise_ground_maximum(height, extra):
    # Identical transport/dispersion (fixed wind); z=0, no plume rise/lid.
    sy, sz = sigmas(np.linspace(100, 10000, 1000), "D")
    low = concentration(10.0, 4.0, sy, sz, 0.0, z=0.0, height=height)
    high = concentration(10.0, 4.0, sy, sz, 0.0, z=0.0, height=height + extra)
    assert high.max() <= low.max() * (1 + 1e-14)


@given(x=st.floats(-10000, 0), y=st.floats(-10000, 10000))
def test_upwind_zero(x, y):
    values, _ = simulate(np.array([x]), np.array([y]), [SOURCE], WEATHER)
    assert values[0] == 0.0


def test_mixing_lid_integral_and_uniform_limit():
    z = np.linspace(0, 200, 4001)
    for sz in [5.0, 80.0, 319.0, 320.0, 1000.0]:
        actual = concentration(10.0, 4.0, 100.0, sz, 0.0, z=z, height=50.0, mixing_height=200.0)
        assert np.trapezoid(actual, z) == pytest.approx(
            10e6 / (np.sqrt(2 * np.pi) * 4 * 100), rel=1e-5
        )
    assert (
        concentration(10.0, 4.0, 100.0, 400.0, 0.0, z=0.0, height=300.0, mixing_height=200.0) == 0
    )


@pytest.mark.parametrize(
    "wind,solar,cloud,day,expected",
    [
        (1, 1000, 0.1, True, "A"),
        (2.5, 800, 0.1, True, "B"),
        (4, 400, 0.1, True, "C"),
        (7, 50, 0.1, True, "D"),
        (2, 0, 0.1, False, "F"),
        (4, 0, 0.1, False, "E"),
        (2, 0, 0.6, False, "E"),
        (4, 0, 0.6, False, "D"),
        (1, 0, 1, False, "D"),
    ],
)
def test_stability_table(wind, solar, cloud, day, expected):
    assert stability_class(wind, solar, cloud, day) == expected


def test_power_profile_and_rise_limits():
    assert wind_at_height(4.0, 100.0, "D", "urban") == pytest.approx(4 * 10**0.25)
    assert wind_at_height(4.0, 5.0, "D", "urban") == pytest.approx(4 * 0.5**0.25)
    assert wind_at_height(0.1, 100.0, "F", "rural") == 1.0
    for stability in "ABCDEF":
        h = effective_height(
            np.array([0.0, 100.0, 1000.0, 10000.0]), 100.0, 2.0, 15.0, 400.0, 293.0, 4.0, stability
        )
        assert np.isfinite(h).all() and (np.diff(h) >= 0).all()
        assert h[0] == 100.0
    assert effective_height(np.array([1000.0]), 10.0, 2.0, 1.0, 293.0, 293.0, 4.0, "D")[0] < 10.0


def test_area_line_mass_conserved():
    for source in [
        {**SOURCE, "type": "area", "width_m": 100, "length_m": 200, "subdivisions": 5},
        {**SOURCE, "type": "line", "end_east_m": 500, "end_north_m": 500, "subdivisions": 20},
    ]:
        assert sum(s["emission_gs"] for s in expand_sources([source])) == pytest.approx(
            source["emission_gs"]
        )


@pytest.mark.parametrize("stability", list("ABCDEF"))
def test_heterogeneous_rising_sources_batch_superposition(stability):
    east, north = np.meshgrid(np.linspace(100, 5000, 25), np.linspace(-1000, 1000, 25))
    sources = [
        {
            **SOURCE,
            "height_m": 30.0,
            "diameter_m": 2.0,
            "exit_velocity_ms": 10.0,
            "exit_temperature_k": 400.0,
        },
        {
            **SOURCE,
            "height_m": 70.0,
            "north_m": 75.0,
            "east_m": 200.0,
            "diameter_m": 1.0,
            "exit_velocity_ms": 20.0,
            "exit_temperature_k": 300.0,
        },
    ]
    weather = {**WEATHER, "stability_class": stability}
    combined, _ = simulate(east, north, sources, weather)
    one, _ = simulate(east, north, [sources[0]], weather)
    two, _ = simulate(east, north, [sources[1]], weather)
    np.testing.assert_allclose(combined, one + two, rtol=2e-6, atol=1e-10)


@pytest.mark.parametrize("name", ["urban-neutral", "rural-unstable", "urban-stable-lid"])
def test_stored_golden_fields(name):
    fixture = json.loads((Path(__file__).parent / "fixtures" / "vayusim-golden.json").read_text())[
        name
    ]
    east, north = np.meshgrid(fixture["east"], fixture["north"])
    actual, _ = simulate(
        east,
        north,
        [fixture["source"]],
        fixture["weather"],
        receptor_height=fixture["receptor_height"],
        environment=fixture["environment"],
    )
    np.testing.assert_allclose(actual, fixture["expected"], rtol=2e-6, atol=1e-12)
