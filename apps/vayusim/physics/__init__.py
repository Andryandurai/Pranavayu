"""NumPy-only educational dispersion engine. No Django or geographic adapters."""

from .engine import ENGINE_VERSION, concentration, expand_sources, simulate
from .meteorology import stability_class, wind_at_height

__all__ = [
    "ENGINE_VERSION",
    "concentration",
    "expand_sources",
    "simulate",
    "stability_class",
    "wind_at_height",
]
