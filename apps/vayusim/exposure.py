"""WorldPop cell-count exposure; conserve counts by warping density, not counts.

Rasterio average warp preserves density; source geographic pixel area is computed
geodesically. Multiply by projected destination cell area. The scenario is local
AEQD; area distortion over10km is negligible, recorded as an approximation.
"""

import numpy as np
import rasterio
from pyproj import Geod
from rasterio.warp import Resampling, reproject, transform_bounds
from rasterio.windows import Window, from_bounds


def population_grid(path, grid, shape, return_support=False):
    with rasterio.open(path) as src:
        bounds = [
            min(p[0] for p in grid["corners"]),
            min(p[1] for p in grid["corners"]),
            max(p[0] for p in grid["corners"]),
            max(p[1] for p in grid["corners"]),
        ]
        source_bounds = transform_bounds("EPSG:4326", src.crs, *bounds, densify_pts=21)
        window = from_bounds(*source_bounds, transform=src.transform)
        window = Window(
            int(np.floor(window.col_off)) - 2,
            int(np.floor(window.row_off)) - 2,
            int(np.ceil(window.width)) + 4,
            int(np.ceil(window.height)) + 4,
        )
        counts = src.read(1, window=window, boundless=True, masked=True).astype(float)
        transform = src.window_transform(window)
        if src.crs.is_geographic:
            geod = Geod(ellps="WGS84")
            areas = []
            for row in range(counts.shape[0]):
                coordinates = [
                    transform @ p for p in [(0, row), (1, row), (1, row + 1), (0, row + 1)]
                ]
                area, _ = geod.polygon_area_perimeter(*zip(*coordinates, strict=True))
                areas.append(abs(area))
            areas = np.asarray(areas)[:, None]
        else:
            areas = abs(transform.a * transform.e - transform.b * transform.d)
        valid = ~np.ma.getmaskarray(counts) & (counts.filled(0) >= 0)
        density = np.where(valid, counts.filled(0) / areas, 0.0)
        destination = np.zeros(shape, dtype=float)
        support = np.zeros(shape, dtype=float)
        for source, target in [(density, destination), (valid.astype(float), support)]:
            # Include the zero arithmetic contribution of unknown source cells
            # in the area denominator, then warp a separate support mask.
            # Ignoring nodata in an average would inflate boundary-cell counts.
            reproject(
                source,
                target,
                src_transform=transform,
                src_crs=src.crs,
                dst_transform=grid["affine"],
                dst_crs=grid["crs"],
                resampling=Resampling.average,
                dst_nodata=np.nan,
            )
        cell_area = abs(grid["affine"].determinant)
        support = np.clip(np.nan_to_num(support, nan=0.0), 0.0, 1.0)
        population = np.where(support > 0, destination * cell_area, np.nan)
        return (population, support) if return_support else population


def exposure_summary(concentration, population, thresholds, support_fraction=None):
    supported = np.isfinite(population) & (population >= 0)
    count = float(np.sum(population[supported]))
    return {
        "label": "hourly added exposure; WorldPop 2025 modelled population",
        "population_support_fraction": float(np.mean(support_fraction))
        if support_fraction is not None
        else float(np.mean(supported)),
        "population_support_scope": "Mean fraction of cell area with population data",
        "partially_supported_cells": int(
            np.sum((support_fraction > 0) & (support_fraction < 1 - 1e-6))
        )
        if support_fraction is not None
        else 0,
        "supported_population": count,
        "population_above": {
            str(t): float(population[supported & (concentration > t)].sum()) for t in thresholds
        },
        "population_weighted_mean_added_ugm3": float(
            np.sum(population[supported] * concentration[supported]) / count
        )
        if count > 0
        else None,
        "missing_population_cells": int((~supported).sum()),
        "method": (
            "geodesic count density; area-weighted warp with fractional support mask; "
            "known population only; unknown area not extrapolated"
        ),
    }
