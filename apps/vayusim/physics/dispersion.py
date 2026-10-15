"""Briggs (1973) closed forms, x in metres, range 100m to 10km.

Penn State METEO532, W.H. Brune, Table2.3 (unpaginated lecture):
https://personal.ems.psu.edu/~brune/m532/m532_theatmosphere.htm
The adjacent worked example has an inconsistent sigma-y; use the table.
"""

import numpy as np

# Each entry: sy a, sy b, sz a, sz b, sz exponent; sy exponent is -1/2.
COEFFICIENTS = {
    "rural": {
        "A": (0.22, 0.0001, 0.20, 0.0, 0.0),
        "B": (0.16, 0.0001, 0.12, 0.0, 0.0),
        "C": (0.11, 0.0001, 0.08, 0.0002, -0.5),
        "D": (0.08, 0.0001, 0.06, 0.0015, -0.5),
        "E": (0.06, 0.0001, 0.03, 0.0003, -1.0),
        "F": (0.04, 0.0001, 0.016, 0.0003, -1.0),
    },
    "urban": {
        "A": (0.32, 0.0004, 0.24, 0.001, 0.5),
        "B": (0.32, 0.0004, 0.24, 0.001, 0.5),
        "C": (0.22, 0.0004, 0.20, 0.0, 0.0),
        "D": (0.16, 0.0004, 0.14, 0.0003, -0.5),
        "E": (0.11, 0.0004, 0.08, 0.0015, -0.5),
        "F": (0.11, 0.0004, 0.08, 0.0015, -0.5),
    },
}


def sigmas(x, stability, environment="urban"):
    x = np.maximum(np.asarray(x, dtype=float), 1.0)
    ay, by, az, bz, power = COEFFICIENTS[environment][stability]
    return ay * x / np.sqrt(1 + by * x), az * x * (1 + bz * x) ** power
