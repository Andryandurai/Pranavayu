"""Exact source sentences and short data tables with explicit provenance."""

import json
import re

STOPWORDS = set(
    (
        "a an the of in on for to with and or is are was were be by as at from what which "
        "how why does do did can could would should tell explain describe report study "
        "paper article according about please"
    ).split()
)


def terms(text):
    return {
        word
        for word in re.findall(r"[a-z][a-z0-9.]+", text.casefold())
        if word not in STOPWORDS and len(word) >= 3
    }


def relevant_sentences(question, text, count=2):
    words = terms(question)
    # Join source line wraps while retaining its words and numeric text exactly.
    continuous = re.sub(r"\s+", " ", text).strip()
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z“])", continuous)
    ranked = []
    for index, sentence in enumerate(sentences):
        overlap = len(words & terms(sentence))
        if overlap and len(sentence) >= 25:
            ranked.append((overlap, index, sentence))
    chosen = sorted(ranked, key=lambda row: (-row[0], row[1]))[:count]
    return [row[2] for row in sorted(chosen, key=lambda row: row[1])]


def scalar(value):
    if isinstance(value, (dict, list)):
        # Bracketed array syntax would look like citation markers in Markdown.
        # Parentheses preserve the ordered values in the displayed evidence row.
        return (
            json.dumps(value, ensure_ascii=False, sort_keys=True)
            .replace("[", "(")
            .replace("]", ")")
        )
    return str(value)


def table_rows(result):
    values = result["values"]
    rows = [("city", result["parameters"]["city"])]
    rows += [(key, value) for key, value in result["parameters"].items() if key != "city"]
    if result["tool"] == "latest_forecast":
        for row in values.get("forecasts", []):
            for key in [
                "issued_for_date",
                "target_date",
                "mode",
                "point",
                "lower80",
                "upper80",
                "lower95",
                "upper95",
                "aqi_category",
                "algorithm",
                "model_version",
                "cohort",
            ]:
                rows.append((f"h{row['horizon']}.{key}", row[key]))
        rows += [
            (key, values[key]) for key in ["units", "timezone", "category_scope", "interpretation"]
        ]
    elif result["tool"] == "city_monthly_series":
        rows += [(row["date"], row["value"]) for row in values["series"][:24]]
        rows.append(("rows_shown", min(24, len(values["series"]))))
        rows.append(("total_rows", len(values["series"])))
        if len(values["series"]) > 24:
            rows.append(
                ("display_limitation", "First 24 months shown; full series in tool_results")
            )
        rows += [(key, value) for key, value in values.items() if key != "series"]
    elif result["tool"] == "data_coverage":
        rows += [
            (str(row["year"]), {k: v for k, v in row.items() if k != "year"})
            for row in values["coverage"]
        ]
    elif result["tool"] == "rq2_drivers":
        rows += [
            (row["period"] + "." + row["feature"], row["mean_abs_daily_shap"])
            for row in values["drivers"]
        ]
        rows += [(key, value) for key, value in values.items() if key != "drivers"]
    elif result["tool"] == "forecast_skill" and values["status"] == "available":
        rows += [(key, value) for key, value in values["policy"].items()]
        rows += [(key, value) for key, value in values.items() if key != "policy"]
    else:
        rows += list(values.items())
    return [
        f"| {field.replace('|', r'\|')} | {scalar(value).replace('|', r'\|')} |"
        for field, value in rows
    ]


def data_evidence(result, alias):
    rows = table_rows(result)
    return {
        "alias": alias,
        "citation": result["citation"],
        "kind": "dataset",
        "text": json.dumps(result, ensure_ascii=False, default=str) + "\n" + "\n".join(rows),
        "rows": rows,
        "status": result["values"].get("status"),
    }


def extractive_answer(question, evidence):
    lines = []
    for item in evidence:
        alias = item["alias"]
        if item["kind"] == "dataset":
            if item["status"] != "available":
                continue
            lines += ["| Field | Value | Citation |", "| --- | --- | --- |"]
            lines += [row + f" [{alias}] |" for row in item["rows"]]
        else:
            for sentence in relevant_sentences(question, item["text"], count=1):
                lines.append(f"{sentence} [{alias}]")
    return "\n".join(lines)
