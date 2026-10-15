"""Source families, with no unsupported facility-parameter defaults.

AP42 emission factors require activity, fuel, controls and size fraction; a
generic factor is not a facility PM2.5 g/s rate. Null fields require input.
"""

AP42 = (
    "https://www.epa.gov/air-emissions-factors-and-quantification/"
    "ap-42-compilation-air-emissions-factors-stationary-sources"
)
PRESETS = [
    {
        "id": "thermal-power",
        "name": "Thermal power plant",
        "type": "point",
        "section": "AP42 Chapter1.1 Bituminous and subbituminous coal combustion",
    },
    {
        "id": "brick-kiln",
        "name": "Brick kiln cluster",
        "type": "area",
        "section": "AP42 Chapter11.3 Brick and structural clay product manufacturing",
    },
    {
        "id": "industrial-boiler",
        "name": "Industrial boiler",
        "type": "point",
        "section": "AP42 Chapter1 External combustion; choose fuel/controls",
    },
    {
        "id": "crop-fire",
        "name": "Crop-fire field",
        "type": "area",
        "section": "AP42 Chapter2.5 Open burning; verify crop/activity and fine fraction",
    },
    {
        "id": "highway",
        "name": "Highway segment",
        "type": "line",
        "section": "AP42 Chapter13.2.1 Paved roads; resuspension only, not tailpipe exhaust",
    },
]


def presets():
    fields = ["height_m", "diameter_m", "exit_velocity_ms", "exit_temperature_k", "emission_gs"]
    return [
        {
            **preset,
            "defaults": dict.fromkeys(fields),
            "required_parameters": fields,
            "citations": [{"url": AP42, "section": preset["section"]}],
            "note": (
                "No universal source-backed facility values were established; enter explicit "
                "assumptions. AP42 factors are not default PM2.5 rates."
            ),
        }
        for preset in PRESETS
    ]
