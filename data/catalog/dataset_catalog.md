# Antarctic Navigation Intelligence — Dataset Catalog

## Project Data Architecture

The project uses multiple real-world datasets for environmental observation,
iceberg detection, trajectory modeling, drift forecasting, and route planning.

Raw datasets are NOT committed to Git.

---

# 1. HYCOM GOFS 3.1 — Surface Ocean Currents

**Role:** Ocean-current forcing for iceberg drift and navigation risk.

- Source: HYCOM GOFS 3.1 / NCODA
- Dataset: `GLBy0.08/expt_93.0/uv3z`
- Period: October 2023
- Temporal resolution: 3-hourly
- Spatial resolution: approximately 1/12°
- Variables:
  - `water_u` — eastward water velocity (m/s)
  - `water_v` — northward water velocity (m/s)
- Vertical level: 0 m
- Requested spatial domain:
  - Latitude: -90° to -55°
  - Longitude: 0° to 360°
- Returned spatial domain:
  - Latitude: -80° to -55°
  - Longitude: 0° to 359.92°
- Files: 31 daily NetCDF4 files
- Each file: 8 time steps
- Total temporal samples: 248
- Format: NetCDF4

### Project usage

HYCOM provides ocean-current forcing for the Lagrangian iceberg drift model.

Conceptually:

`iceberg movement = ocean current + wind forcing + stochastic component`

---

# 2. ERA5 — Atmospheric Environment

**Role:** Atmospheric forcing and environmental conditions.

- Period: October 2023
- Temporal resolution: hourly
- Spatial domain: 55°S–90°S
- Variables:
  - `u10` — 10 m eastward wind component
  - `v10` — 10 m northward wind component
  - `t2m` — 2 m temperature
- Format: GRIB

### Important limitation

The current ERA5 file does NOT contain significant wave height.

`meanSea` is metadata/coordinate information and must NOT be interpreted as wave height.

---

# 3. NSIDC-0051 Version 2 — Sea Ice Concentration

**Role:** Sea-ice environment and navigation constraint.

- Product: NSIDC-0051 Version 2
- Grid: 25 km polar stereographic
- Antarctic CRS: EPSG:3412
- Period downloaded: October 2023
- Variable:
  - `F17_ICECON` — sea ice concentration
- Units: fraction from 0 to 1
- Format: NetCDF

### Project usage

Sea-ice concentration will contribute to:

- navigation constraints
- route risk
- environmental state
- ice exposure estimation

---

# 4. BYU/NIC Iceberg Database

**Role:** Historical iceberg trajectories and trajectory validation.

Two archives are available:

### Stats Database v7.1

File:

`stats_database_v7.1.zip`

Contains daily iceberg records including fields such as:

- date
- date gap
- displacement
- latitude
- longitude
- mask
- size
- velocity angle

### Consolidated Database v8.0

File:

`consolidated_database_v8.0.zip`

Contains historical iceberg/sensor information including:

- ASCAT
- ERS
- NIC
- NSCAT
- OSCAT
- QSCAT
- SeaWinds
- iceberg size information

### Project usage

BYU/NIC is the primary historical source for:

- iceberg trajectories
- drift validation
- trajectory statistics
- historical motion patterns

---

# 5. Circum-Antarctic Iceberg Vector Dataset

**Role:** Antarctic/Southern Ocean iceberg spatial distribution and geometry context.

- Snapshot: October 2023
- Coverage: Southern Ocean south of 55°S
- Features: 44,537
- CRS: EPSG:3031
- Format: GeoPackage

### Geometry

- Polygon
- MultiPolygon
- GeometryCollection

### Attributes

- longitude
- latitude
- area
- area uncertainty
- perimeter
- long axis
- short axis
- mass
- mass uncertainty

### Project usage

Used for:

- iceberg spatial context
- iceberg geometry
- visualization
- route-risk context
- comparison with other iceberg observations

This is an annual spatial snapshot and is NOT a continuous trajectory dataset.

---

# 6. Antarctic Grounded Iceberg Sentinel-1 Dataset

**Role:** Grounded iceberg detection and segmentation reference.

- Features: 39,619
- Geometry: Polygon
- CRS: EPSG:3031
- Source: Sentinel-1 SAR
- Format: GeoPackage

### Available attributes

- iceberg identifier
- acquisition information
- timestamp/date range
- area
- latitude
- longitude
- projected coordinates
- bathymetry-related information
- fast-ice overlap information

### Important limitation

These are grounded/stationary icebergs.

They must NOT be treated as a moving iceberg trajectory dataset.

### Project usage

Used for:

- iceberg detection reference
- segmentation
- grounded iceberg identification
- spatial validation

---

# Integrated Data Flow

```text
                 ┌──────────────┐
                 │    ERA5      │
                 │ Wind / Temp  │
                 └──────┬───────┘
                        │
                        ▼
┌──────────────┐   ┌───────────────┐   ┌──────────────┐
│    HYCOM     │──►│ Environmental │◄──│    NSIDC     │
│ Ocean Curr.  │   │     State     │   │ Sea Ice      │
└──────────────┘   └───────┬───────┘   └──────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │ Drift Model  │
                    └──────┬───────┘
                           ▲
                           │
                    ┌──────┴───────┐
                    │              │
               ┌───────┐      ┌────────────┐
               │  BYU  │      │ Circum-    │
               │ Tracks│      │ Antarctic  │
               └───────┘      └────────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │ Risk Assessment │
                  └────────┬────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │ Route Optimizer │
                  └────────┬────────┘
                           │
                           ▼
                 Antarctic Navigation
                    Intelligence