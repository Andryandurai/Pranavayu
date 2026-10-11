"""Transparent deterministic routes/tool parameters; every call is validated again."""

import re

from apps.warehouse.models import City


def city_mentions(question):
    folded = question.casefold()
    matches = []
    for city in City.objects.all():
        aliases = [city.slug, city.name.casefold()]
        aliases += {"bengaluru": ["bangalore"], "kolkata": ["calcutta"]}.get(city.slug, [])
        if any(re.search(r"\b" + re.escape(alias) + r"\b", folded) for alias in aliases):
            matches.append(city.slug)
    return matches


def route_question(question):
    lower = question.casefold()
    cities = city_mentions(question)
    years = [int(year) for year in re.findall(r"\b(19\d{2}|20\d{2})\b", question)]
    calls = []
    for city in cities:
        parameters = {"city": city}
        tool = None
        if any(
            term in lower
            for term in ["forecast skill", "forecast rmse", "skill versus", "forecast evaluation"]
        ):
            match = re.search(r"(?:horizon\s*|h|t\s*\+\s*)([123])\b", lower)
            tool, parameters = (
                "forecast_skill",
                {**parameters, "horizon": int(match[1]) if match else 1},
            )
        elif "forecast" in lower and any(
            term in lower for term in ["latest", "current", "next", "replay"]
        ):
            tool = "latest_forecast"
        elif "coverage" in lower or "data available" in lower:
            tool = "data_coverage"
        elif "ncap" in lower and any(
            term in lower for term in ["comparison", "proxy", "change", "progress"]
        ):
            tool = "ncap_proxy_comparison"
        elif "driver" in lower or "shap" in lower:
            season = (
                "pre_monsoon"
                if "pre-monsoon" in lower or "pre_monsoon" in lower
                else "monsoon"
                if "monsoon" in lower
                else "winter"
            )
            tool, parameters = "rq2_drivers", {**parameters, "season": season}
        elif "monthly" in lower and (len(years) >= 1):
            dates = re.findall(r"\b\d{4}-\d{2}-\d{2}\b", question)
            start = dates[0] if dates else f"{min(years)}-01-01"
            end = dates[1] if len(dates) >= 2 else f"{max(years) + 1}-01-01"
            kind = (
                "deweathered"
                if "deweather" in lower or "normalised" in lower or "normalized" in lower
                else "raw"
            )
            tool, parameters = (
                "city_monthly_series",
                {**parameters, "start": start, "end": end, "kind": kind},
            )
        elif years and any(term in lower for term in ["exceed", "above", "over the threshold"]):
            threshold = re.search(r"(?:above|threshold|exceeding)\s*([0-9]+(?:\.[0-9]+)?)", lower)
            tool, parameters = (
                "exceedance_days",
                {
                    **parameters,
                    "year": years[0],
                    "threshold": float(threshold[1]) if threshold else 60.0,
                },
            )
        elif years and any(
            term in lower for term in ["annual mean", "annual average", "yearly mean"]
        ):
            tool, parameters = "city_annual_mean", {**parameters, "year": years[0]}
        if tool:
            calls.append({"tool": tool, "parameters": parameters})
    if not calls:
        return "literature", []
    literature = any(
        term in lower
        for term in [
            "according to",
            "guideline",
            "paper",
            "research study",
            "why ",
            "explain",
            "standard",
        ]
    )
    return "mixed" if literature else "data", calls
