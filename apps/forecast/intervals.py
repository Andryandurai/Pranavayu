"""Post-Phase-4 interval policy, selected from existing archived-weather scores.

Selection uses the completed evaluation by explicit user request. Its coverage is
retrospective, not an independent test of the newly selected policy. No fit or
point-prediction parameter is changed.
"""

import numpy as np


def choose_interval_policy(result):
    choices = {}
    for nominal in (80, 95):
        target = nominal / 100
        candidates = []
        for method, prefix in (("conformal", ""), ("quantile_lightgbm", "quantile_")):
            score = result["intervals"][f"{prefix}{nominal}"]
            candidates.append({"method": method, **score})
        eligible = [c for c in candidates if c["coverage"] >= target - 0.05 - 1e-12]
        chosen = min(
            eligible or candidates, key=lambda c: (abs(c["coverage"] - target), c["method"])
        )
        choices[str(nominal)] = {
            **chosen,
            "nominal": target,
            "coverage_gate_passed": bool(eligible),
            "warning": "" if eligible else "No existing method meets the five-point tolerance",
        }
    return {
        "version": 1,
        "choices": choices,
        "evaluation_window": [result["target_start"], result["target_end"]],
        "selection": "closest empirical coverage, requiring nominal minus 0.05 when possible",
        "evaluation_weather": "archived_forecast",
        "post_evaluation_selection": True,
        "independent_validation": False,
        "point_model_changed": False,
    }


def apply_interval_policy(values, policy):
    """Keep the point fixed; select saved interval families and ensure nesting."""
    selected = dict(values)
    for nominal, choice in policy.get("choices", {}).items():
        prefix = "quantile_" if choice["method"] == "quantile_lightgbm" else ""
        for side in ("lower", "upper"):
            selected[f"{side}{nominal}"] = np.asarray(values[f"{prefix}{side}{nominal}"]).copy()
    selected["lower95"] = np.minimum(selected["lower95"], selected["lower80"])
    selected["upper95"] = np.maximum(selected["upper95"], selected["upper80"])
    return selected
