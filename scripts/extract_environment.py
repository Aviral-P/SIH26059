from pathlib import Path
import math
import pandas as pd
import xarray as xr
from pyproj import Transformer


ROOT = Path(__file__).resolve().parents[1]

HYCOM_DIR = ROOT / "data/raw/hycom"
ERA5_FILE = ROOT / "data/raw/era5/era5_2023_10.grib"
NSIDC_DIR = ROOT / "data/raw/nsidc"


def load_era5():
    """
    Load ERA5 atmosphere and wave groups separately.

    Atmosphere:
        u10, v10, t2m

    Waves:
        swh

    SWH may legitimately be missing at a requested location.
    """

    atmosphere = xr.open_dataset(
        ERA5_FILE,
        engine="cfgrib",
        backend_kwargs={
            "indexpath": ""
        }
    )

    waves = xr.open_dataset(
        ERA5_FILE,
        engine="cfgrib",
        backend_kwargs={
            "filter_by_keys": {
                "shortName": "swh"
            },
            "indexpath": ""
        }
    )

    return atmosphere, waves


def load_hycom(timestamp):
    date_str = timestamp.strftime("%Y-%m-%d")

    path = HYCOM_DIR / f"hycom_{date_str}.nc4"

    if not path.exists():
        raise FileNotFoundError(
            f"HYCOM file not found: {path}"
        )

    return xr.open_dataset(path)


def load_nsidc(timestamp):
    date_str = timestamp.strftime("%Y%m%d")

    path = NSIDC_DIR / f"NSIDC0051_SEAICE_PS_S25km_{date_str}_v2.0.nc"

    if not path.exists():
        raise FileNotFoundError(
            f"NSIDC file not found: {path}"
        )

    return xr.open_dataset(path)


def extract_hycom(ds, timestamp, lat, lon):

    # HYCOM uses 0-360 longitude
    hycom_lon = lon % 360

    point = ds.sel(
        time=timestamp,
        depth=0,
        lat=lat,
        lon=hycom_lon,
        method="nearest"
    )

    u = float(point["water_u"].values)
    v = float(point["water_v"].values)

    available = math.isfinite(u) and math.isfinite(v)

    if not available:
        u = None
        v = None
        speed = None
    else:
        speed = math.sqrt(u * u + v * v)

    return {
        "u": u,
        "v": v,
        "speed": speed,
        "available": available
    }


def extract_era5(atmosphere, waves, timestamp, lat, lon):

    # ERA5 uses -180 ... +180
    era5_lon = ((lon + 180) % 360) - 180

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
        wind_speed = math.sqrt(u10 * u10 + v10 * v10)
    else:
        u10 = None
        v10 = None
        wind_speed = None

    if not temperature_available:
        t2m = None

    # -------------------------
    # Optional wave information
    # -------------------------

    wave_point = waves.sel(
        time=timestamp,
        latitude=lat,
        longitude=era5_lon,
        method="nearest"
    )

    swh = float(wave_point["swh"].values)

    wave_available = math.isfinite(swh)

    if not wave_available:
        swh = None

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


def extract_nsidc(ds, lat, lon):

    transformer = Transformer.from_crs(
        "EPSG:4326",
        "EPSG:3412",
        always_xy=True
    )

    x, y = transformer.transform(lon, lat)

    point = ds.sel(
        x=x,
        y=y,
        method="nearest"
    )

    # Remove the single time dimension if present
    sic_values = point["F17_ICECON"].values

    sic = float(sic_values.squeeze())

    # NSIDC special flag values:
    # 251 = pole hole
    # 252 = mask
    # 253 = unused
    # 254 = coast

    if not math.isfinite(sic) or sic >= 251:
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


def extract_environment(timestamp, lat, lon):

    print("\nLoading environmental datasets...")

    era5_atmosphere, era5_waves = load_era5()

    hycom = load_hycom(timestamp)

    nsidc = load_nsidc(timestamp)

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
            "available": atmosphere["temperature_available"]
        },

        "wave": {
            "swh": atmosphere["swh"],
            "available": atmosphere["wave_available"]
        },

        "sea_ice": sea_ice
    }


if __name__ == "__main__":

    timestamp = pd.Timestamp("2023-10-01T12:00:00")

    result = extract_environment(
        timestamp,
        lat=-65.0,
        lon=40.0
    )

    print("\n" + "=" * 60)
    print("ENVIRONMENTAL STATE")
    print("=" * 60)

    import pprint
    pprint.pprint(result, sort_dicts=False)