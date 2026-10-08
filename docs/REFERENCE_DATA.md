# Reference seed provenance

The seed contains published standards and source metadata, plus approximate city
centre coordinates. It contains no measured or simulated observations. Values below
are in the pollutant's stored unit; never compare measurements in different units or
with different averaging periods.

| Code | Unit | WHO 2021 short-term AQG | WHO hours | NAAQS 24-hour |
| --- | --- | --- | --- | --- |
| pm25 | µg/m³ | 15 | 24 | 60 |
| pm10 | µg/m³ | 45 | 24 | 100 |
| no2 | µg/m³ | 25 | 24 | 80 |
| so2 | µg/m³ | 40 | 24 | 80 |
| co | mg/m³ | 4 | 24 | null |
| o3 | µg/m³ | 100 | 8 | null |
| nh3 | µg/m³ | null | null | 400 |

WHO values follow the [WHO 2021 global air quality guidelines](https://www.who.int/publications/i/item/9789240034228/)
and the [WHO-published summary table](https://www.ncbi.nlm.nih.gov/books/NBK574582/table/fm-ch1.tab1/).
Short-term percentile/exceedance definitions apply; these are not instantaneous
thresholds. WHO's ozone value is an 8-hour value, not a 24-hour guideline. The seed
does not attempt to store the separate annual or peak-season standards.

India's 24-hour limits follow CPCB's notification of 18 November 2009, reproduced in
[CPCB's NAAQS report, Annexure 2](https://cpcb.gov.in/upload/NAAQS_2019.pdf)
and the [official notification hosted by UNEP](https://leap.unep.org/en/akn/in/act/2009/b-29016-20-90-pci-l/eng%402009-11-18).
CO has 8-hour/1-hour limits (2/4 mg/m³) and ozone has 8-hour/1-hour limits
(100/180 µg/m³); neither supplies a NAAQS 24-hour value. Those values must not be
invented or copied into the 24-hour field. There is no WHO 2021 numerical NH3 AQG.

The following points are approximate urban reference locations in WGS84, suitable
for an initial catalogue. They are not centroids computed from administrative
polygons, station coordinates, or claims of population-weighted centres. Seed
population and administrative boundaries remain null. The map links expose each
reference location for curator review.

| City | State code | Latitude | Longitude | Reference location |
| --- | --- | --- | --- | --- |
| Delhi | DL | 28.6139 | 77.2090 | [Map](https://www.openstreetmap.org/#map=12/28.6139/77.2090) |
| Mumbai | MH | 19.0760 | 72.8777 | [Map](https://www.openstreetmap.org/#map=12/19.0760/72.8777) |
| Kolkata | WB | 22.5726 | 88.3639 | [Map](https://www.openstreetmap.org/#map=12/22.5726/88.3639) |
| Chennai | TN | 13.0827 | 80.2707 | [Map](https://www.openstreetmap.org/#map=12/13.0827/80.2707) |
| Bengaluru | KA | 12.9716 | 77.5946 | [Map](https://www.openstreetmap.org/#map=12/12.9716/77.5946) |
| Hyderabad | TS | 17.3850 | 78.4867 | [Map](https://www.openstreetmap.org/#map=12/17.3850/78.4867) |
| Ahmedabad | GJ | 23.0225 | 72.5714 | [Map](https://www.openstreetmap.org/#map=12/23.0225/72.5714) |
| Pune | MH | 18.5204 | 73.8567 | [Map](https://www.openstreetmap.org/#map=12/18.5204/73.8567) |
| Lucknow | UP | 26.8467 | 80.9462 | [Map](https://www.openstreetmap.org/#map=12/26.8467/80.9462) |
| Kanpur | UP | 26.4499 | 80.3319 | [Map](https://www.openstreetmap.org/#map=12/26.4499/80.3319) |
| Patna | BR | 25.5941 | 85.1376 | [Map](https://www.openstreetmap.org/#map=12/25.5941/85.1376) |
| Jaipur | RJ | 26.9124 | 75.7873 | [Map](https://www.openstreetmap.org/#map=12/26.9124/75.7873) |

Initial NCAP flags follow the [CPCB list of non-attainment cities](https://cpcb.nic.in/uploads/non-attainment_cities.pdf)
and [PRANA's list of 131 cities](https://prana.cpcb.gov.in/ncapDashboard/download_public_portal_file/Minutes_of_National_Apex_Committee_meeting_march_15th.pdf),
including Bengaluru under its earlier Bangalore name. These are reference snapshots;
the flag is not evidence of a current measured violation. Curators should revisit
classification and geographic identity before policy-impact research.

The twelve source homepages are stored in `apps/warehouse/reference.py`:

| Source | Provider |
| --- | --- |
| CPCB CCR | [CPCB continuous monitoring](https://airquality.cpcb.gov.in/ccr/) |
| OpenAQ | [OpenAQ](https://openaq.org/) |
| data.gov.in | [Open Government Data India](https://www.data.gov.in/) |
| ERA5 | [Copernicus Climate Data Store](https://cds.climate.copernicus.eu/) |
| IMD | [India Meteorological Department](https://mausam.imd.gov.in/) |
| NASA FIRMS | [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/) |
| Sentinel-5P | [Copernicus Data Space](https://dataspace.copernicus.eu/) |
| MODIS MAIAC | [NASA Earthdata](https://www.earthdata.nasa.gov/) |
| WorldPop | [WorldPop](https://www.worldpop.org/) |
| Datameet maps | [Datameet boundary repository](https://github.com/datameet/maps) |
| VAHAN | [VAHAN public dashboard](https://vahan.parivahan.gov.in/vahan4dashboard/) |
| PRANA | [CPCB PRANA](https://prana.cpcb.gov.in/) |

Access methods describe intended entry points, not implemented connectors or
promised unrestricted APIs. Licence notes are product-dependent and instruct later
ingestion to check the chosen dataset's actual reuse conditions and attribution.
Source keys and city slugs are stable identifiers; the seed is atomic and repeatable.
