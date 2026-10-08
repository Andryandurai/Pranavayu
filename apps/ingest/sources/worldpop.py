import json

from django.contrib.gis.gdal import GDALRaster

from apps.ingest.base import Source, SourceUnavailable


class WorldPopSource(Source):
    slug = "worldpop"
    name = "WorldPop"
    url = "https://hub.worldpop.org/geodata/summary?id=73812"
    licence = "CC BY 4.0; cite WorldPop DOI 10.5258/SOTON/WP00839 and product release statement."
    dataset_url = (
        "https://data.worldpop.org/GIS/Population/Global_2015_2030/R2025A/2030/IND/"
        "v1/100m/constrained/ind_pop_2030_CN_100m_R2025A_v1.tif"
    )
    filename = "worldpop/ind_pop_2030_CN_100m_R2025A_v1.tif"

    def download(self, **options):
        self.download_asset(self.url, "worldpop/catalogue-73812.html")
        # The public HTTPS server ignored Range and transferred very slowly.
        # The provider documents anonymous FTP with the same file layout:
        # https://sdi.worldpop.org/wpdata . Resume the verified cached prefix.
        ftp_url = self.dataset_url.replace("https://data.worldpop.org", "ftp://ftp.worldpop.org")
        path, manifest = self.cache.download_ftp(
            ftp_url,
            self.filename,
            metadata={
                "year": 2030,
                "projected": True,
                "product": "R2025A v1 alpha constrained",
                "resolution": "3 arc seconds (approximately 100 m at equator)",
                "units": "people per pixel",
                "doi": "10.5258/SOTON/WP00839",
                "https_url": self.dataset_url,
                "ftp_documentation": "https://sdi.worldpop.org/wpdata",
            },
        )
        self.register_asset(path, manifest)

    def load(self, **options):
        path = self.cache.root / self.filename
        if not path.exists():
            raise SourceUnavailable("WorldPop GeoTIFF not downloaded")
        path, asset = self.local_asset(path)
        raster = GDALRaster(str(path))
        metadata = {
            **asset.metadata,
            "srid": raster.srs.srid,
            "width": raster.width,
            "height": raster.height,
            "bands": len(raster.bands),
            "nodata": raster.bands[0].nodata_value,
            "origin": [raster.origin.x, raster.origin.y],
            "scale": [raster.scale.x, raster.scale.y],
        }
        changed = asset.metadata != metadata
        asset.metadata = metadata
        asset.save(update_fields=["metadata", "updated_at"])
        manifest_path = path.with_name(path.name + ".manifest.json")
        manifest = json.loads(manifest_path.read_text())
        manifest["metadata"] = metadata
        manifest_path.write_text(json.dumps(manifest, indent=2))
        self.run.rows_fetched = 1
        self.run.rows_inserted = int(changed)
        self.run.params["asset_id"] = asset.pk
        self.event("raster_registered", asset_id=asset.pk, path=asset.path, **metadata)
