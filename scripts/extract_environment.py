from pathlib import Path
import math
import argparse
import pandas as pd
import xarray as xr
from pyproj import Transformer


ROOT = Path(__file__).resolve().parents[1]

# -------------------------
# Production / normal data
# -------------------------

HYCOM_DIR = ROOT / "data/raw/hycom"
ERA5_FILE = ROOT / "data/raw/era5/era5_2023_10.grib"
NSIDC_DIR = ROOT / "data/raw/nsidc"

# -------------------------
# Historical validation data
# -------------------------

HYCOM_VALIDATION_DIR = ROOT / "data/raw/hycom_validation"
ERA5_VALIDATION_FILE = ROOT / "data/raw/era5/era5_2023_07_validation.nc"
NSIDC_VALIDATION_DIR = ROOT / "data/raw/nsidc_validation"


# ============================================================
# ERA5
# ============================================================

def load_era5(validation=False):
    """
    Load ERA5 atmosphere and wave fields.

    Production:
        ERA5 October GRIB with atmosphere + SWH groups.

    Validation:
        July validation NetCDF containing u10, v10, t2m.

    Waves are optional.
    """

    if validation:

        if not ERA5_VALIDATION_FILE.exists():
            raise FileNotFoundError(
                f"ERA5 validation file not found: "
                f"{ERA5_VALIDATION_FILE}"
            )

        atmosphere = xr.open_dataset(
            ERA5_VALIDATION_FILE
        )

        # Historical validation file does not contain SWH.
        waves = None

        return atmosphere, waves

    # Production GRIB

    import cfgrib

    datasets = cfgrib.open_datasets(
        str(ERA5_FILE),
        backend_kwargs={
            "indexpath": ""
        }
    )

    atmosphere = None
    waves = None

    for ds in datasets:

        variables = set(ds.data_vars)

        if {"u10", "v10", "t2m"}.issubset(variables):
            atmosphere = ds

        if "swh" in variables:
            waves = ds

    if atmosphere is None:
        raise RuntimeError(
            "Could not locate ERA5 atmosphere dataset "
            "(u10, v10, t2m)."
        )

    # Waves are optional.
    # Do not fail if SWH is unavailable.

    return atmosphere, waves


# ============================================================
# HYCOM
# ============================================================

def load_hycom(timestamp, validation=False):

    date_str = timestamp.strftime("%Y-%m-%d")

    if validation:

        path = (
            HYCOM_VALIDATION_DIR /
            f"d29c_hycom_20230721_24.nc"
        )

    else:

        path = (
            HYCOM_DIR /
            f"hycom_{date_str}.nc4"
        )

    if not path.exists():
        raise FileNotFoundError(
            f"HYCOM file not found: {path}"
        )

    return xr.open_dataset(path)


# ============================================================
# NSIDC
# ============================================================

def load_nsidc(timestamp, validation=False):

    date_str = timestamp.strftime("%Y%m%d")

    if validation:

        path = (
            NSIDC_VALIDATION_DIR /
            f"NSIDC0051_SEAICE_PS_S25km_{date_str}_v2.0.nc"
        )

    else:

        path = (
            NSIDC_DIR /
            f"NSIDC0051_SEAICE_PS_S25km_{date_str}_v2.0.nc"
        )

    if not path.exists():
        raise FileNotFoundError(
            f"NSIDC file not found: {path}"
        )

    return xr.open_dataset(path)


# ============================================================
# HYCOM extraction
# ============================================================

def extract_hycom(ds, timestamp, lat, lon):

    # HYCOM uses 0-360 longitude
    hycom_lon = lon % 360

    # Normalize the requested timestamp to timezone-naive UTC.
    # HYCOM files may expose time as datetime64[ns], while API
    # timestamps can arrive as timezone-aware datetime64[us, UTC].
    timestamp = pd.Timestamp(timestamp)
    if timestamp.tzinfo is not None:
        timestamp = timestamp.tz_convert("UTC").tz_localize(None)

    # Normalize HYCOM's time coordinate to the same timezone-naive
    # representation before xarray performs the nearest lookup.
    if "time" in ds.coords:
        hycom_times = pd.to_datetime(ds["time"].values)

        if getattr(hycom_times, "tz", None) is not None:
            hycom_times = hycom_times.tz_convert("UTC").tz_localize(None)

        ds = ds.assign_coords(time=hycom_times)

    point = ds.sel(
        time=timestamp,
        lat=lat,
        lon=hycom_lon,
        method="nearest",
    )

    u = float(point["water_u"].isel(depth=0).values.squeeze())
    v = float(point["water_v"].isel(depth=0).values.squeeze())

    available = (
        math.isfinite(u)
        and math.isfinite(v)
    )

    if not available:

        u = None
        v = None
        speed = None

    else:

        speed = math.sqrt(
            u * u + v * v
        )

    return {
        "u": u,
        "v": v,
        "speed": speed,
        "available": available
    }


# ============================================================
# ERA5 extraction
# ============================================================

def extract_era5(
    atmosphere,
    waves,
    timestamp,
    lat,
    lon
):

    # ERA5 uses -180 ... +180
    era5_lon = ((lon + 180) % 360) - 180

    # Normalize API timestamps to timezone-naive UTC so they can be
    # compared safely with xarray/pandas datetime coordinates.
    timestamp = pd.Timestamp(timestamp)
    if timestamp.tzinfo is not None:
        timestamp = timestamp.tz_convert("UTC").tz_localize(None)

    # Handle validation ERA5 which uses valid_time
    if "valid_time" in atmosphere.coords:

        era5_times = pd.to_datetime(
            atmosphere["valid_time"].values
        )

        if getattr(era5_times, "tz", None) is not None:
            era5_times = era5_times.tz_convert("UTC").tz_localize(None)

        atmosphere = atmosphere.assign_coords(
            valid_time=era5_times
        )

        point = atmosphere.sel(
            valid_time=timestamp,
            latitude=lat,
            longitude=era5_lon,
            method="nearest"
        )

    else:

        era5_times = pd.to_datetime(
            atmosphere["time"].values
        )

        if getattr(era5_times, "tz", None) is not None:
            era5_times = era5_times.tz_convert("UTC").tz_localize(None)

        atmosphere = atmosphere.assign_coords(
            time=era5_times
        )

        point = atmosphere.sel(
            time=timestamp,
            latitude=lat,
            longitude=era5_lon,
            method="nearest"
        )

    u10 = float(point["u10"].values)
    v10 = float(point["v10"].values)
    t2m = float(point["t2m"].values)

    wind_available = (
        math.isfinite(u10)
        and math.isfinite(v10)
    )

    temperature_available = math.isfinite(t2m)

    if wind_available:

        wind_speed = math.sqrt(
            u10 * u10 + v10 * v10
        )

    else:

        u10 = None
        v10 = None
        wind_speed = None

    if not temperature_available:
        t2m = None

    # -------------------------
    # Optional wave information
    # -------------------------

    swh = None
    wave_available = False

    if waves is not None:

        try:

            wave_point = waves.sel(
                time=timestamp,
                latitude=lat,
                longitude=era5_lon,
                method="nearest"
            )

            swh = float(
                wave_point["swh"].values
            )

            wave_available = math.isfinite(swh)

            if not wave_available:
                swh = None

        except Exception:

            swh = None
            wave_available = False

    return {

        "u10": u10,
        "v10": v10,
        "wind_speed": wind_speed,
        "wind_available": wind_available,

        "t2m": t2m,
        "temperature_available": temperature_available,

        "swh": swh,
        "wave_available": wave_available
    }


# ============================================================
# NSIDC extraction
# ============================================================

def extract_nsidc(ds, lat, lon):

    transformer = Transformer.from_crs(
        "EPSG:4326",
        "EPSG:3412",
        always_xy=True
    )

    x, y = transformer.transform(
        lon,
        lat
    )

    point = ds.sel(
        x=x,
        y=y,
        method="nearest"
    )

    sic_values = point[
        "F17_ICECON"
    ].values

    sic = float(
        sic_values.squeeze()
    )

    # NSIDC special flag values:
    # 251 = pole hole
    # 252 = mask
    # 253 = unused
    # 254 = coast

    if (
        not math.isfinite(sic)
        or sic >= 251
    ):

        return {
            "concentration": None,
            "available": False
        }

    if not 0.0 <= sic <= 1.0:

        return {
            "concentration": None,
            "available": False
        }

    return {
        "concentration": sic,
        "available": True
    }


# ============================================================
# MAIN ENVIRONMENT EXTRACTION
# ============================================================

def extract_environment(
    timestamp,
    lat,
    lon,
    validation=False
):

    print("\nLoading environmental datasets...")

    era5_atmosphere, era5_waves = load_era5(
        validation=validation
    )

    hycom = load_hycom(
        timestamp,
        validation=validation
    )

    nsidc = load_nsidc(
        timestamp,
        validation=validation
    )

    print("Extracting HYCOM...")

    ocean = extract_hycom(
        hycom,
        timestamp,
        lat,
        lon
    )

    print("Extracting ERA5...")

    atmosphere = extract_era5(
        era5_atmosphere,
        era5_waves,
        timestamp,
        lat,
        lon
    )

    print("Extracting NSIDC...")

    sea_ice = extract_nsidc(
        nsidc,
        lat,
        lon
    )

    # Close datasets after extraction
    era5_atmosphere.close()

    if era5_waves is not None:
        era5_waves.close()

    hycom.close()
    nsidc.close()

    return {

        "timestamp": timestamp.isoformat(),

        "latitude": lat,

        "longitude": lon,

        "ocean_current": ocean,

        "wind": {

            "u": atmosphere["u10"],

            "v": atmosphere["v10"],

            "speed": atmosphere["wind_speed"],

            "available": atmosphere["wind_available"]

        },

        "temperature": {

            "t2m": atmosphere["t2m"],

            "available":
                atmosphere[
                    "temperature_available"
                ]

        },

        "wave": {

            "swh": atmosphere["swh"],

            "available":
                atmosphere[
                    "wave_available"
                ]

        },

        "sea_ice": sea_ice
    }


# ============================================================
# COMMAND LINE INTERFACE
# ============================================================

def parse_args():

    parser = argparse.ArgumentParser(
        description=(
            "Extract Antarctic environmental "
            "conditions for a given position/time."
        )
    )

    parser.add_argument(
        "--timestamp",
        required=False,
        default="2023-10-01T12:00:00",
        help=(
            "Timestamp in ISO format. "
            "Example: 2023-07-21T00:00:00"
        )
    )

    parser.add_argument(
        "--lat",
        required=False,
        type=float,
        default=-65.0,
        help="Latitude"
    )

    parser.add_argument(
        "--lon",
        required=False,
        type=float,
        default=40.0,
        help="Longitude"
    )

    parser.add_argument(
        "--validation",
        action="store_true",
        help=(
            "Use historical July validation "
            "datasets instead of production datasets."
        )
    )

    return parser.parse_args()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    args = parse_args()

    timestamp = pd.Timestamp(
        args.timestamp
    )

    result = extract_environment(
        timestamp=timestamp,
        lat=args.lat,
        lon=args.lon,
        validation=args.validation
    )

    print("\n" + "=" * 60)
    print("ENVIRONMENTAL STATE")
    print("=" * 60)

    import pprint

    pprint.pprint(
        result,
        sort_dicts=False
    )