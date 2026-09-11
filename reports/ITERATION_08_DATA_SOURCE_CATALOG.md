# SkyGuard AI — High-quality data source catalog for Iteration 8

Date verified: 2026-08-29  
Scope: SIH26073 temperature, atmospheric pressure and relative humidity anomaly detection

No finite list can contain every weather-data site in the world. This catalog prioritizes official meteorological agencies, documented quality control, reproducible access and variables relevant to SkyGuard.

## Recommended source order

| Priority | Source | T/P/RH suitability | Cadence | Access | Best SkyGuard use |
|---:|---|---|---|---|---|
| 1 | [DWD CDC 10-minute observations](https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/10_minutes/air_temperature/) | Direct T, station P, RH | 10 min | Open HTTPS bulk | Iteration 8 primary new corpus; cadence/frozen/drift/weather curriculum |
| 2 | [NOAA/NCEI Global Hourly ISD](https://www.ncei.noaa.gov/products/land-based-station/integrated-surface-database) | T and P direct; RH direct or derived from dew point | Hourly/synoptic | Open HTTPS bulk/search | India baseline, global climate diversity and quality flags |
| 3 | [MPI-BGC Jena weather-station archive](https://weather.bgc-jena.mpg.de/weather_data.html) | Direct T, air pressure and RH | 10 min | Open ZIP/CSV, CC-BY-4.0 | Independent single-site normal-sequence/reconstruction check; not spatial-neighbour validation |
| 4 | [MeteoSwiss SwissMetNet AWS](https://opendata.swiss/en/dataset/automatische-wetterstationen-messwerte) | Direct T, QFE/QFF pressure and RH | 10 min/hourly | Open CSV/STAC | Mountain-domain and unseen-network transfer |
| 5 | [IMD Current Weather API documentation](https://mausam.imd.gov.in/imd_latest/contents/api.pdf) | Current T, MSLP and RH | Current observations | Public-IP whitelist required | India live SIH demonstration; not the main historical training source |
| 6 | [UK Met Office MIDAS Open hourly](https://catalogue.ceda.ac.uk/uuid/d04207b551674c07801b7d4e6d883e50/) | Direct T, station/MSL pressure, calculated RH | Hourly | Free registration/download | Independent maritime climate validation |
| 7 | [Environment and Climate Change Canada Historical Climate Data](https://climate.weather.gc.ca/) | T, station pressure and RH where available | Hourly | Open portal/bulk methods | Cold-climate transfer and seasonal extremes |
| 8 | [NOAA MADIS surface mesonet](https://madis.ncep.noaa.gov/sfc_mesonet_variable_list.shtml) | T, RH and pressure/altimeter with QC levels | Near-real-time | Documented NOAA access | Live multi-network feed and QC comparison |
| 9 | [NOAA ASOS five-minute observations](https://www.ncei.noaa.gov/access/search/datasets/auto-surf-obs-sys-5-min/) | T, pressure and RH | 5 min | NCEI download/search | High-frequency communication/frozen-fault testing |
| 10 | [Iowa Environmental Mesonet ASOS archive](https://mesonet.agron.iastate.edu/ASOS/) | T, RH, altimeter/MSL pressure | 1–10 min ingest | Open scripted service | Easy live/offline replay prototype; retain NOAA provenance |
| 11 | [JMA AMeDAS](https://www.jma.go.jp/jma/en/Activities/amedas/amedas.html) | T/RH widely available; pressure at surface stations | 10 min/current | Web/CSV guidance | Dense Asian AWS network and typhoon/front behaviour |
| 12 | [Australian Bureau of Meteorology Climate Data Online](https://www.bom.gov.au/climate/data/) | T, RH, station/MSL pressure products | Subdaily/daily varies | Open portal; some products ordered | Hot/arid/coastal external validation |
| 13 | [NOAA U.S. Climate Reference Network](https://www.ncei.noaa.gov/access/crn/data.html) | Excellent T/RH; pressure is not a core product | 5 min/hourly | Open quality-controlled files | Sensor-quality reference and hard-negative T/RH patterns, not full T/P/RH benchmark |
| 14 | [WMO WIS 2.0 / wis2box data access](https://docs.wis2box.wis.wmo.int/en/1.0b7/reference/data-access/python-api-requests.html) | SYNOP surface observations can include T/P/RH | Real time/hourly | Global-cache/API/broker workflow | Standards-based scalable live-stream adapter |
| 15 | [ECMWF Copernicus ERA5 single levels](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels) | 2 m T/dew point and surface/MSL pressure; derive RH | Hourly | Free account/API, CC-BY | Regional-event corroboration and neighbour context; never a sensor-fault label |
| 16 | [NASA MERRA-2](https://disc.gsfc.nasa.gov/datasets?keywords=MERRA-2) | Near-surface T, pressure and humidity fields | Hourly/3-hourly product dependent | Free Earthdata account | Independent reanalysis comparison and uncertainty context |
| 17 | [JMA JRA-55](https://jra.kishou.go.jp/JRA-55/index_en.html) | Surface T, P and RH/dew-point deficit products | 3 hourly for common surface fields | Registration/product download | Independent reanalysis confirmation |
| 18 | [WMO OSCAR/Surface](https://oscar.wmo.int/surface/) | Metadata, instruments and station capabilities | Metadata | Open consultation/export | Authoritative station identity, location, elevation and instrument history |

## Discovery portals: use with provenance checks

These sites can reveal useful research datasets but should not replace official station data without checking creator, licence, collection protocol, sensor units, station metadata and checksums:

- [Zenodo](https://zenodo.org/)
- [Mendeley Data](https://data.mendeley.com/)
- [Harvard Dataverse](https://dataverse.harvard.edu/)
- [IEEE DataPort](https://ieee-dataport.org/)
- [PANGAEA](https://www.pangaea.de/)
- [Figshare](https://figshare.com/)
- [UCI Machine Learning Repository](https://archive.ics.uci.edu/)
- [OpenML](https://www.openml.org/)
- [Kaggle Datasets](https://www.kaggle.com/datasets)

Kaggle, personal-weather-station aggregators and convenience forecast APIs are useful for prototyping, but they are not accepted as SkyGuard's principal scientific benchmark unless each underlying observation has an official source and reproducible lineage.

## Iteration 8 frozen selection

Iteration 8 uses 16 DWD stations arranged into four neighbour groups:

- north coastal;
- east continental;
- west lowland;
- south upland.

The selected official station archives contain long historical records. Only 2022 and 2023 are normalized for model development. DWD 2024 is packaged separately as a locked external confirmation partition, and every DWD/NOAA 2025 observation remains excluded from all tuning.

The primary DWD product stores station-level pressure. SkyGuard preserves that raw value and creates an explicit sea-level-reduced pressure field using station elevation and current temperature so it is comparable with the existing NOAA MSL-pressure contract. This transform is recorded in every row and must be included in the methodology.

## Data-use rules

1. Train only on genuine observations that pass source-level missing/range checks.
2. Never treat ERA5, MERRA-2 or JRA-55 as proof that a station sensor is faulty; they provide regional context only.
3. Keep fault labels synthetic and reproducible unless an official source explicitly confirms a malfunction.
4. Split complete incidents by station, climate, time and event family.
5. Preserve provider quality flags, raw pressure, station elevation, source URL, file hash and transformation version.
6. Keep the detector's meteorological inputs limited to temperature, pressure and relative humidity, as required by SIH26073.
