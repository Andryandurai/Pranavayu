"""Real reference metadata only. Citations and averaging periods: docs/REFERENCE_DATA.md."""

# code, display name, unit, WHO short-term value, WHO hours, NAAQS 24h
POLLUTANTS = (
    ("pm25", "PM2.5", "µg/m³", 15, 24, 60),
    ("pm10", "PM10", "µg/m³", 45, 24, 100),
    ("no2", "Nitrogen dioxide", "µg/m³", 25, 24, 80),
    ("so2", "Sulfur dioxide", "µg/m³", 40, 24, 80),
    ("co", "Carbon monoxide", "mg/m³", 4, 24, None),
    ("o3", "Ozone", "µg/m³", 100, 8, None),
    ("nh3", "Ammonia", "µg/m³", None, None, 400),
)

# name, slug, homepage, access method, licence/access note, description
SOURCES = (
    (
        "CPCB CCR",
        "cpcb-ccr",
        "https://airquality.cpcb.gov.in/ccr/",
        "manual",
        "Check CPCB terms and station-provider attribution before redistribution.",
        "Central Control Room for India's continuous ambient air quality monitoring.",
    ),
    (
        "OpenAQ",
        "openaq",
        "https://openaq.org/",
        "api",
        "Data-provider licences apply; review OpenAQ API terms and attribute providers.",
        "Public air-quality observations aggregated from monitoring networks.",
    ),
    (
        "data.gov.in",
        "data-gov-in",
        "https://www.data.gov.in/",
        "api",
        "Government Open Data License - India; confirm each resource's metadata.",
        "India's Open Government Data platform, including air-quality resources.",
    ),
    (
        "ERA5",
        "era5",
        "https://cds.climate.copernicus.eu/",
        "api",
        "Copernicus licence; acknowledge ECMWF and the Copernicus Climate Change Service.",
        "ECMWF atmospheric reanalysis via the Climate Data Store.",
    ),
    (
        "IMD",
        "imd",
        "https://mausam.imd.gov.in/",
        "manual",
        "Product-specific IMD access and reuse terms; some archives require permission.",
        "India Meteorological Department weather observations and products.",
    ),
    (
        "NASA FIRMS",
        "nasa-firms",
        "https://firms.modaps.eosdis.nasa.gov/",
        "api",
        "NASA Earth science data policy; acknowledge FIRMS and instrument data providers.",
        "Satellite active-fire detections from MODIS and VIIRS.",
    ),
    (
        "Sentinel-5P",
        "sentinel-5p",
        "https://dataspace.copernicus.eu/",
        "api",
        "Copernicus Sentinel data terms; acknowledge Copernicus Sentinel data.",
        "TROPOMI atmospheric composition products from Sentinel-5P.",
    ),
    (
        "MODIS MAIAC",
        "modis-maiac",
        "https://www.earthdata.nasa.gov/",
        "download",
        "NASA Earth science data policy; cite the selected MAIAC product and version.",
        "MODIS MAIAC aerosol optical depth products (MCD19A2).",
    ),
    (
        "WorldPop",
        "worldpop",
        "https://www.worldpop.org/",
        "download",
        "CC BY 4.0 for standard WorldPop datasets; confirm the selected product's licence.",
        "Gridded population estimates with product-specific years and methods.",
    ),
    (
        "Datameet maps",
        "datameet-maps",
        "https://github.com/datameet/maps",
        "download",
        "CC BY 4.0; boundary accuracy and provenance require review.",
        "Community-maintained Indian administrative boundaries.",
    ),
    (
        "VAHAN",
        "vahan",
        "https://vahan.parivahan.gov.in/vahan4dashboard/",
        "manual",
        "Check Ministry of Road Transport and Highways portal terms; no assumed open API.",
        "Vehicle registration statistics from the VAHAN public dashboard.",
    ),
    (
        "PRANA",
        "prana",
        "https://prana.cpcb.gov.in/",
        "manual",
        "Check CPCB portal terms and city-plan licences before downloading/reuse.",
        "NCAP city action-plan implementation and progress portal.",
    ),
)

# name, state name, stable project state code, longitude, latitude
CITIES = (
    ("Delhi", "Delhi", "DL", 77.2090, 28.6139),
    ("Mumbai", "Maharashtra", "MH", 72.8777, 19.0760),
    ("Kolkata", "West Bengal", "WB", 88.3639, 22.5726),
    ("Chennai", "Tamil Nadu", "TN", 80.2707, 13.0827),
    ("Bengaluru", "Karnataka", "KA", 77.5946, 12.9716),
    ("Hyderabad", "Telangana", "TS", 78.4867, 17.3850),
    ("Ahmedabad", "Gujarat", "GJ", 72.5714, 23.0225),
    ("Pune", "Maharashtra", "MH", 73.8567, 18.5204),
    ("Lucknow", "Uttar Pradesh", "UP", 80.9462, 26.8467),
    ("Kanpur", "Uttar Pradesh", "UP", 80.3319, 26.4499),
    ("Patna", "Bihar", "BR", 85.1376, 25.5941),
    ("Jaipur", "Rajasthan", "RJ", 75.7873, 26.9124),
)
