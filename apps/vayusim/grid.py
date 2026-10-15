"""Geographic adapters; the NumPy engine has no projection or Django imports."""

import numpy as np
from affine import Affine
from pyproj import CRS, Transformer


def build_grid(centre, wind_direction, width_m=10000, resolution_m=50):
    crs = CRS.from_proj4(f"+proj=aeqd +lat_0={centre[1]} +lon_0={centre[0]} +datum=WGS84 +units=m")
    forward = Transformer.from_crs(4326, crs, always_xy=True)
    inverse = Transformer.from_crs(crs, 4326, always_xy=True)
    theta = np.deg2rad((wind_direction + 180) % 360)
    ne, nn = np.sin(theta), np.cos(theta)
    pe, pn = -nn, ne
    affine = Affine(
        ne * resolution_m,
        -pe * resolution_m,
        -width_m / 2 * ne + width_m / 2 * pe,
        nn * resolution_m,
        -pn * resolution_m,
        -width_m / 2 * nn + width_m / 2 * pn,
    )
    size = int(round(width_m / resolution_m))
    columns, rows = np.meshgrid(np.arange(size) + 0.5, np.arange(size) + 0.5)
    east, north = affine @ (columns, rows)
    corners = [
        list(inverse.transform(*(affine @ pixel)))
        for pixel in [(0, 0), (size, 0), (size, size), (0, size)]
    ]
    return {
        "east": east,
        "north": north,
        "crs": crs,
        "affine": affine,
        "forward": forward,
        "inverse": inverse,
        "corners": corners,
    }


def project_sources(sources, grid):
    result = []
    for source in sources:
        east, north = grid["forward"].transform(*source["location"])
        item = {**source, "east_m": east, "north_m": north}
        if source["type"] == "line":
            item["end_east_m"], item["end_north_m"] = grid["forward"].transform(
                *source["end_location"]
            )
        result.append(item)
    return result
