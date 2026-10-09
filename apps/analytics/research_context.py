"""Official reference verification and canonical, multi-pollutant table rebuilding."""

import hashlib
import json
import re
from pathlib import Path

import pandas as pd

from apps.warehouse.models import City

from .aggregation import analysis_dataframe, build_tables
from .lifecycle import analysis_run
from .models import CityCoverage, CitySeries


def verify_ncap():
    path = Path("data/raw/research_library/ncap_city_list.pdf")
    text = path.with_suffix(".txt").read_text()
    cities = {
        "bengaluru": ("Bangalore", 43),
        "delhi": ("Delhi", 26),
        "hyderabad": ("Hyderabad", 101),
        "kanpur": ("Kanpur", 113),
        "lucknow": ("Lucknow", 115),
        "mumbai": ("Mumbai", 63),
        "pune": ("Pune", 67),
        "ahmedabad": ("Ahmedabad", 28),
        "chennai": ("Chennai*", 100),
        "jaipur": ("Jaipur", 93),
        "kolkata": ("Kolkata", 125),
        "patna": ("Patna", 19),
    }
    records = []
    for city in City.objects.all():
        name, index = cities[city.slug]
        if not re.search(rf"\b{index}\.\s*{re.escape(name)}", text):
            raise ValueError(f"Official NCAP document does not contain expected entry {name}")
        status = not name.endswith("*")
        records.append(
            dict(
                city=city.slug,
                official_name=name,
                entry=index,
                is_ncap_nonattainment=status,
                previous_value=city.is_ncap_nonattainment,
                ncap_participant=True,
                source="https://cpcb.gov.in/uploads/Non-Attainment_Cities.pdf",
                source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                note="Starred cities are million-plus participants, not non-attainment"
                if not status
                else "Unstarred non-attainment city",
            )
        )
        if city.is_ncap_nonattainment != status:
            city.is_ncap_nonattainment = status
            city.save(update_fields=["is_ncap_nonattainment"])
    return records


def rebuild_stored_tables(diagnostic_run_id):
    with analysis_run(
        name="phase3b-data",
        start="2015-01-01",
        end="2025-12-31",
        parent_data_run=diagnostic_run_id,
        clock_version="opencity-ist-clock-v1",
    ) as (run, output):
        result = build_tables(run, output)
        equivalence = []
        for city in City.objects.all():
            canonical = analysis_dataframe(city.slug, run)
            reference = analysis_dataframe(city.slug, 7)
            fields = ["observed_at", "value", "station_count"]
            pd.testing.assert_frame_equal(
                canonical[fields].reset_index(drop=True),
                reference[fields].reset_index(drop=True),
                check_dtype=False,
                check_exact=False,
                rtol=1e-12,
                atol=1e-12,
            )
            equivalence.append(dict(city=city.slug, rows=len(canonical), equivalent_to_run7=True))
        ncap = verify_ncap()
        (output / "ncap_official_verification.json").write_text(json.dumps(ncap, indent=2))
        (output / "canonical_equivalence.json").write_text(json.dumps(equivalence, indent=2))
        run.results = dict(**result, equivalence=equivalence, ncap=ncap)
    return run.pk


def pm10_context(run_id, city):
    records = []
    for year in [2024, 2025]:
        coverage = CityCoverage.objects.filter(
            run_id=run_id, city=city, pollutant__code="pm10", year=year
        ).first()
        if coverage is None or not coverage.hours_present:
            records.append(dict(year=year, status="unavailable", reason="No observed PM10"))
            continue
        daily = CitySeries.objects.filter(
            run_id=run_id,
            city=city,
            pollutant__code="pm10",
            frequency="daily",
            kind="raw",
            date__year=year,
            value__isnull=False,
        )
        values = list(daily.values_list("value", flat=True))
        records.append(
            dict(
                year=year,
                status="recent context only",
                mean_pm10=float(pd.Series(values).mean()) if values else None,
                valid_days=len(values),
                eligible=coverage.eligible,
                baseline_pm10_available=False,
                is_official_compliance_result=False,
            )
        )
    return records
