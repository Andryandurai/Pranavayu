import os
import uuid
import zipfile
from contextlib import ExitStack
from datetime import UTC

import cdsapi
import netCDF4
from django.conf import settings

from apps.ingest.base import Source, SourceUnavailable
from apps.ingest.units import humidity_from_dewpoint, number, to_utc, wind_from_components
from apps.warehouse.models import City, WeatherObservation

from .openmeteo import OpenMeteoSource


class ERA5Source(Source):
    slug = "era5"
    name = "ERA5"
    url = "https://cds.climate.copernicus.eu/"
    licence = "Copernicus licence; cite ECMWF and Copernicus Climate Change Service."
    access_method = "api"

    def load_netcdf(self, path, city):
        path, asset = self.local_asset(path, product="reanalysis-era5-single-levels")
        paths = [path]
        if zipfile.is_zipfile(path):
            paths = []
            with zipfile.ZipFile(path) as archive:
                for name in archive.namelist():
                    target = self.cache.path(f"era5/extracted/{asset.sha256}/{name}")
                    if name.endswith(".nc"):
                        target.write_bytes(archive.read(name))
                        self.local_asset(target, parent_asset=asset.pk)
                        paths.append(target)
            if not paths:
                raise ValueError("CDS ZIP contains no NetCDF files")
        # CDS can split instantaneous/accumulated variables into separate files.
        # Combine by timestamp before inserting; otherwise the first file's UUID
        # would conflict and silently discard variables from the second file.
        with ExitStack() as stack:
            datasets = [stack.enter_context(netCDF4.Dataset(p)) for p in paths]
            variables = {
                name: (dataset, variable)
                for dataset in datasets
                for name, variable in dataset.variables.items()
            }
            timevar = variables.get("valid_time", variables.get("time", (None, None)))[1]
            if timevar is None:
                raise ValueError("ERA5 NetCDF has no time variable")
            times = netCDF4.num2date(
                timevar[:],
                timevar.units,
                only_use_cftime_datetimes=False,
                only_use_python_datetimes=True,
            )
            objects, metadata = [], {}

            def value(key, index):
                if key not in variables:
                    return None
                dataset, variable = variables[key]
                selectors = []
                for dimension in variable.dimensions:
                    if dimension in {"time", "valid_time"}:
                        selectors.append(index)
                    elif dimension in {"latitude", "longitude"}:
                        coordinates = dataset.variables[dimension][:]
                        target = city.location.y if dimension == "latitude" else city.location.x
                        selectors.append(abs(coordinates - target).argmin())
                    elif len(dataset.dimensions[dimension]) == 1:
                        selectors.append(0)
                    else:
                        raise ValueError(f"Unsupported ERA5 dimension: {dimension}")
                item = variable[tuple(selectors)]
                return None if getattr(item, "mask", False) else number(item)

            for index, timestamp in enumerate(times):
                instant = to_utc(timestamp, UTC)
                identifier = uuid.uuid5(
                    uuid.NAMESPACE_URL, f"era5:cds:{city.slug}:{instant.isoformat()}"
                )
                temp, dew = value("t2m", index), value("d2m", index)
                temp = temp - 273.15 if temp is not None else None
                dew = dew - 273.15 if dew is not None else None
                speed, direction = wind_from_components(value("u10", index), value("v10", index))
                pressure, solar, rain = value("sp", index), value("ssrd", index), value("tp", index)
                objects.append(
                    WeatherObservation(
                        id=identifier,
                        observed_at=instant,
                        city=city,
                        location=city.location,
                        source=self.source,
                        temperature_c=temp,
                        relative_humidity=humidity_from_dewpoint(temp, dew),
                        wind_speed_ms=speed,
                        wind_dir_deg=direction,
                        boundary_layer_height_m=value("blh", index),
                        surface_pressure_hpa=pressure / 100 if pressure is not None else None,
                        solar_radiation_wm2=solar / 3600 if solar is not None else None,
                        total_cloud_cover=value("tcc", index),
                        precipitation_mm=rain * 1000 if rain is not None else None,
                    )
                )
                metadata[identifier] = {
                    "dew_point_2m_c": dew,
                    "model": "ERA5 CDS",
                    "solar_accumulation": "one hour",
                }
                self.run.rows_fetched += 1
                if len(objects) >= settings.INGEST_BATCH_SIZE:
                    self.insert_observations(
                        WeatherObservation, objects, "weather", asset, metadata
                    )
                    objects, metadata = [], {}
            self.insert_observations(WeatherObservation, objects, "weather", asset, metadata)

    def load(self, start=None, end=None, **options):
        key = os.environ.get("CDS_API_KEY")
        if not key:
            raise SourceUnavailable("skipped: no key")
        client = cdsapi.Client(
            url=os.environ.get("CDS_API_URL", "https://cds.climate.copernicus.eu/api"),
            key=key,
            timeout=settings.INGEST_HTTP_TIMEOUT,
            retry_max=settings.INGEST_HTTP_ATTEMPTS,
        )
        for city in City.objects.all():
            for first, last in OpenMeteoSource.windows(start, end):
                try:
                    path = self.cache.path(f"era5/{city.slug}/{first}_{last}.nc")
                    if not path.exists():
                        # CDS point requests use a tiny grid area; do not download a
                        # global cube. Daily windows avoid selecting dates outside range.
                        current = first
                        from datetime import timedelta

                        while current <= last:
                            daily = self.cache.path(f"era5/{city.slug}/{current}.nc")
                            if not daily.exists():
                                client.retrieve(
                                    "reanalysis-era5-single-levels",
                                    {
                                        "product_type": ["reanalysis"],
                                        "variable": [
                                            "2m_temperature",
                                            "2m_dewpoint_temperature",
                                            "10m_u_component_of_wind",
                                            "10m_v_component_of_wind",
                                            "boundary_layer_height",
                                            "surface_pressure",
                                            "surface_solar_radiation_downwards",
                                            "total_cloud_cover",
                                            "total_precipitation",
                                        ],
                                        "year": [str(current.year)],
                                        "month": [f"{current.month:02}"],
                                        "day": [f"{current.day:02}"],
                                        "time": [f"{hour:02}:00" for hour in range(24)],
                                        "area": [
                                            city.location.y,
                                            city.location.x,
                                            city.location.y,
                                            city.location.x,
                                        ],
                                        "data_format": "netcdf",
                                        "download_format": "unarchived",
                                    },
                                    str(daily),
                                )
                            self.load_netcdf(daily, city)
                            current += timedelta(days=1)
                    else:
                        self.load_netcdf(path, city)
                except Exception as exc:
                    self.fail_asset(f"{city.slug}:{first}:{last}", exc)
