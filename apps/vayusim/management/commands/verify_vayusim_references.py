"""Compare unchanged physics with manually transcribed external references."""

import hashlib
import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.vayusim.physics import concentration
from apps.vayusim.physics.dispersion import COEFFICIENTS, sigmas


class Command(BaseCommand):
    help = "Report independent numeric cases, scheme differences and unvalidated branches"

    def add_arguments(self, parser):
        parser.add_argument("--output", default="data/results/phase6a-independent/comparisons.json")

    def handle(self, *args, **options):
        path = settings.BASE_DIR / "tests/fixtures/vayusim-independent-references.json"
        fixture = json.loads(path.read_text())
        for source in fixture["sources"].values():
            if source.get("repo_sha256"):
                body = (settings.BASE_DIR / source["repo_path"]).read_bytes()
                if hashlib.sha256(body).hexdigest() != source["repo_sha256"]:
                    raise ValueError("Cached reference identity changed: " + source["repo_path"])
        results = []

        def add(case, variable, expected, actual, tolerance, method, eligible=None):
            difference = 100 * abs(float(actual) - expected) / abs(expected)
            results.append(
                {
                    "case": case["id"],
                    "source": case["source"],
                    "variable": variable,
                    "reference": expected,
                    "engine": float(actual),
                    "absolute_percentage_error": difference,
                    "tolerance_percent": tolerance * 100,
                    "within_tolerance": difference <= tolerance * 100,
                    "eligible_for_case_validation": (
                        case["eligible_for_case_validation"] if eligible is None else eligible
                    ),
                    "method": method,
                }
            )

        for case in fixture["numeric_cases"]:
            sy, sz = sigmas(case["x_m"], case["stability"], case["environment"])
            tolerance = fixture["tolerances"]["printed_sigma_relative"]
            if case["reference_kind"] == "chart-read":
                tolerance = fixture["tolerances"]["chart_read_relative"]
            add(case, "sigma_y_m", case["sigma_y_m"], sy, tolerance, "engine sigma")
            add(case, "sigma_z_m", case["sigma_z_m"], sz, tolerance, "engine sigma")
            rows = case.get("rows", [])
            if "concentration_ugm3" in case:
                rows = [
                    {"z_m": case["receptor_z_m"], "concentration_ugm3": case["concentration_ugm3"]}
                ]
            for row in rows:
                for method, supplied_sy, supplied_sz in [
                    ("engine sigma -> Gaussian, prescribed H/u", sy, sz),
                    (
                        "Gaussian only, source-supplied sigmas/H/u",
                        case["sigma_y_m"],
                        case["sigma_z_m"],
                    ),
                ]:
                    value = concentration(
                        case["q_gs"],
                        case["transport_wind_ms"],
                        supplied_sy,
                        supplied_sz,
                        case["receptor_y_m"],
                        z=row["z_m"],
                        height=case["effective_height_m"],
                    )
                    add(
                        case,
                        f"concentration_ugm3 at z={row['z_m']:g} m",
                        row["concentration_ugm3"],
                        value,
                        fixture["tolerances"]["concentration_relative"],
                        method,
                        eligible=False,
                    )
        urban = fixture["urban_equation_transcription"]["rows"]
        equation_coverage = {
            stability: list(COEFFICIENTS["urban"][stability]) == coefficients
            for stability, coefficients in urban.items()
        }
        eligible = [row for row in results if row["eligible_for_case_validation"]]
        output = {
            "fixture_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "fixture": fixture,
            "comparisons": results,
            "urban_equation_transcription_matches": equation_coverage,
            "independent_numeric_passes": sum(row["within_tolerance"] for row in eligible),
            "independent_numeric_failures": sum(not row["within_tolerance"] for row in eligible),
            "independently_validated_cases": ["rural/D sigmas at 1000 m"]
            if eligible and all(row["within_tolerance"] for row in eligible)
            else [],
            "example_branches": fixture["example_branch_gate"],
            "gate": "Ready for 6B with caveats",
            "gate_condition": (
                "Phase 6B must show an 'unvalidated branch' label for urban C and F "
                "before presenting these scenarios; no Phase 6B implementation in this task"
            ),
            "physical_field_validity": "not established",
            "end_to_end_plume_rise_validity": "not established",
        }
        target = Path(options["output"])
        if not target.is_absolute():
            target = settings.BASE_DIR / target
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(output, indent=2) + "\n")
        for row in results:
            scope = (
                "independent numeric" if row["eligible_for_case_validation"] else "diagnostic only"
            )
            status = "PASS" if row["within_tolerance"] else "FAIL tolerance"
            self.stdout.write(
                f"{row['case']} | {row['variable']} | {row['method']} | "
                f"reference={row['reference']:.9g} engine={row['engine']:.12g} "
                f"error={row['absolute_percentage_error']:.6f}% "
                f"tolerance={row['tolerance_percent']:g}% | {status}; {scope}"
            )
        self.stdout.write(
            json.dumps(
                {
                    key: value
                    for key, value in output.items()
                    if key not in {"fixture", "comparisons"}
                },
                indent=2,
            )
        )
