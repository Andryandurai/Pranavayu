from .sources.boundaries import BoundarySource
from .sources.cpcb_archive import CPCBArchiveSource
from .sources.era5 import ERA5Source
from .sources.firms import FIRMSsource
from .sources.openaq import OpenAQSource
from .sources.opencity import OpenCitySource
from .sources.openmeteo import OpenMeteoSource
from .sources.worldpop import WorldPopSource

SOURCES = {
    "boundaries": BoundarySource,
    "cpcb": CPCBArchiveSource,
    "opencity": OpenCitySource,
    "weather": OpenMeteoSource,
    "worldpop": WorldPopSource,
    "openaq": OpenAQSource,
    "firms": FIRMSsource,
    "era5": ERA5Source,
}
PUBLIC_SOURCES = ("boundaries", "cpcb", "opencity", "weather", "worldpop")
