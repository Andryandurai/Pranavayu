"""Reflected Gaussian fields; concentrations returned in µg/m³, Q in g/s."""

import numpy as np

from .dispersion import sigmas
from .meteorology import wind_at_height
from .rise import effective_height

ENGINE_VERSION = "gaussian-briggs-1.1.0"


def concentration(q_gs, u_ms, sigma_y, sigma_z, y, z=1.5, height=0.0, mixing_height=None):
    """Gaussian primitive with independently supplied dispersion coefficients.

    ISC3 VolII Eq1-50, printed pp.1-32--1-33: reflected image series;
    switch at sigma-z/L>=1.6 to vertical uniform mixing. Effective release
    above the lid is excluded (inversion penetration), not folded below it.
    Relative convergence is elementwise, including tiny nonzero tails.
    """
    sy, sz, yy, zz, hh = np.broadcast_arrays(sigma_y, sigma_z, y, z, height)
    vertical = np.exp(-0.5 * ((zz - hh) / sz) ** 2) + np.exp(-0.5 * ((zz + hh) / sz) ** 2)
    if mixing_height is not None:
        lid = float(mixing_height)
        if lid <= 0:
            raise ValueError("Mixing height must be positive")
        mixed = sz >= 1.6 * lid
        active = ~mixed & (hh <= lid) & (zz <= lid)
        for n in range(1, 100):
            addition = sum(
                np.exp(-0.5 * ((zz + sign * hh + shift * 2 * n * lid) / sz) ** 2)
                for sign in (-1, 1)
                for shift in (-1, 1)
            )
            vertical += np.where(active, addition, 0.0)
            if np.all(~active | (addition <= 1e-6 * np.maximum(vertical, np.finfo(float).tiny))):
                break
        else:
            raise ArithmeticError("Mixing-lid images did not converge")
        vertical = np.where(mixed, np.sqrt(2 * np.pi) * sz / lid, vertical)
        vertical = np.where((hh <= lid) & (zz <= lid), vertical, 0.0)
    return q_gs * 1e6 / (2 * np.pi * u_ms * sy * sz) * np.exp(-0.5 * (yy / sy) ** 2) * vertical


def expand_sources(sources):
    """Area midpoint lattice / line midpoint segments, conserving total Q.

    These are documented numerical point approximations, not ISC area/line
    integrals. Refinement is user-controlled; near-field peaks depend on it.
    Local coordinates are east/north metres, geographic conversion is external.
    """
    result = []
    for source in sources:
        kind = source.get("type", "point")
        if kind == "point":
            result.append(dict(source))
            continue
        count = source["subdivisions"]
        if kind == "area":
            offsets = (np.arange(count) + 0.5) / count - 0.5
            xx, yy = np.meshgrid(offsets * source["width_m"], offsets * source["length_m"])
            positions = np.column_stack(
                (xx.ravel() + source["east_m"], yy.ravel() + source["north_m"])
            )
        elif kind == "line":
            fraction = (np.arange(count) + 0.5) / count
            positions = np.column_stack(
                (
                    source["east_m"] + fraction * (source["end_east_m"] - source["east_m"]),
                    source["north_m"] + fraction * (source["end_north_m"] - source["north_m"]),
                )
            )
        else:
            raise ValueError("Unknown source type")
        result.extend(
            {
                **source,
                "type": "point",
                "east_m": float(e),
                "north_m": float(n),
                "emission_gs": source["emission_gs"] / len(positions),
            }
            for e, n in positions
        )
    return result


def simulate(east, north, sources, weather, receptor_height=1.5, environment="urban"):
    """Vectorised receptors with bounded source batches, linear superposition."""
    east, north = np.broadcast_arrays(east, north)
    total = np.zeros(east.shape, dtype=float)
    theta = np.deg2rad((weather["wind_direction_deg"] + 180) % 360)
    ne, nn = np.sin(theta), np.cos(theta)
    flags = set()
    if weather["wind_speed_ms"] < 1:
        flags.add("low-wind: Gaussian plume unreliable")
    if weather.get("mixing_height_m") is not None and receptor_height > weather["mixing_height_m"]:
        flags.add("Receptor above mixing lid: concentration excluded")
    points = expand_sources(sources)
    # Source/receptor broadcasting in bounded batches avoids a Python loop per
    # source while keeping400x400 grids within a predictable memory envelope.
    for offset in range(0, len(points), 20):
        batch = points[offset : offset + 20]
        shape = (len(batch),) + (1,) * east.ndim
        columns = {
            field: np.asarray([s[field] for s in batch], dtype=float).reshape(shape)
            for field in [
                "east_m",
                "north_m",
                "emission_gs",
                "height_m",
                "diameter_m",
                "exit_velocity_ms",
                "exit_temperature_k",
            ]
        }
        if np.any(
            (columns["exit_temperature_k"] < weather["temperature_k"])
            & (columns["exit_velocity_ms"] > 0)
        ):
            flags.add("Cold exhaust: momentum-only rise; dense-gas sinking not modelled")
        de, dn = east - columns["east_m"], north - columns["north_m"]
        x, y = de * ne + dn * nn, -de * nn + dn * ne
        active = x >= 1.0
        if np.any(active & ((x < 100) | (x > 10000))):
            flags.add("Briggs coefficients extrapolated outside 100m–10km")
        sy, sz = sigmas(x, weather["stability_class"], environment)
        u = wind_at_height(
            weather["wind_speed_ms"], columns["height_m"], weather["stability_class"], environment
        )
        if np.any(u <= 1.0):
            flags.add("low-wind: Gaussian plume unreliable; release-height wind floored at1m/s")
        h = effective_height(
            x,
            columns["height_m"],
            columns["diameter_m"],
            columns["exit_velocity_ms"],
            columns["exit_temperature_k"],
            weather["temperature_k"],
            u,
            weather["stability_class"],
        )
        lid = weather.get("mixing_height_m")
        if lid is not None and np.any(active & (h > lid)):
            flags.add("Effective release above mixing lid: ground contribution excluded")
        values = concentration(columns["emission_gs"], u, sy, sz, y, receptor_height, h, lid)
        total += np.where(active, values, 0.0).sum(axis=0)
    if any(s.get("type") in {"area", "line"} for s in sources):
        flags.add("Area/line point discretisation: near-field peaks depend on subdivisions")
    return total.astype(np.float32), sorted(flags)
