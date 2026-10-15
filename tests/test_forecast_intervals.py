import numpy as np

from apps.forecast.intervals import apply_interval_policy, choose_interval_policy


def test_existing_interval_selection_has_an_explicit_no_eligible_path():
    result = {
        "target_start": "2025-07-01",
        "target_end": "2025-12-31",
        "intervals": {
            "80": {"coverage": 0.685, "n": 184},
            "quantile_80": {"coverage": 0.804, "n": 184},
            "95": {"coverage": 0.82, "n": 184},
            "quantile_95": {"coverage": 0.87, "n": 184},
        },
    }
    policy = choose_interval_policy(result)
    assert policy["choices"]["80"]["method"] == "quantile_lightgbm"
    assert policy["choices"]["80"]["coverage_gate_passed"]
    assert not policy["choices"]["95"]["coverage_gate_passed"]
    assert policy["choices"]["95"]["warning"]
    values = {
        "prediction": np.array([20.0]),
        "lower80": np.array([17.0]),
        "upper80": np.array([23.0]),
        "lower95": np.array([15.0]),
        "upper95": np.array([25.0]),
        "quantile_lower80": np.array([10.0]),
        "quantile_upper80": np.array([30.0]),
        "quantile_lower95": np.array([12.0]),
        "quantile_upper95": np.array([28.0]),
    }
    applied = apply_interval_policy(values, policy)
    np.testing.assert_array_equal(applied["prediction"], values["prediction"])
    assert applied["lower95"][0] == 10 and applied["upper95"][0] == 30
    assert values["lower95"][0] == 15
