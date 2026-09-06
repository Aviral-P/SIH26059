from pathlib import Path
import glob
import os

import pandas as pd
import xarray as xr


ROOT = Path(__file__).resolve().parents[1]

CALIBRATION_FILE = ROOT / "data/catalog/calibration_observations.csv"
ERA5_DIR = ROOT / "data/raw/era5/extracted"


def find_era5_files():
    return sorted(
        set(
            glob.glob(
                str(ERA5_DIR / "**/*.nc"),
                recursive=True
            )
        )
    )


def load_era5_files():
    datasets = []

    for path in find_era5_files():
        try:
            ds = xr.open_dataset(path)

            if "u10" not in ds.data_vars or "v10" not in ds.data_vars:
                print(f"Skipping {os.path.basename(path)}: missing u10/v10")
                ds.close()
                continue

            datasets.append(
                {
                    "path": path,
                    "ds": ds,
                    "lat_min": float(ds.latitude.min()),
                    "lat_max": float(ds.latitude.max()),
                    "lon_min": float(ds.longitude.min()),
                    "lon_max": float(ds.longitude.max()),
                }
            )

        except Exception as exc:
            print(f"Could not open {path}: {exc}")

    return datasets


def find_dataset(datasets, latitude, longitude):
    candidates = []

    for item in datasets:
        if (
            item["lat_min"] <= latitude <= item["lat_max"]
            and item["lon_min"] <= longitude <= item["lon_max"]
        ):
            candidates.append(item)

    if not candidates:
        return None

    return candidates[0]


def extract_wind(item, timestamp, latitude, longitude):
    ds = item["ds"]

    timestamp = pd.Timestamp(timestamp)

    try:
        point = ds.sel(
            valid_time=timestamp,
            latitude=latitude,
            longitude=longitude,
            method="nearest",
        )

        u10 = float(point["u10"].values)
        v10 = float(point["v10"].values)

        return {
            "u": u10,
            "v": v10,
            "available": True,
        }

    except Exception:
        return {
            "u": None,
            "v": None,
            "available": False,
        }


def main():
    df = pd.read_csv(CALIBRATION_FILE)

    datasets = load_era5_files()

    print(f"Calibration pairs: {len(df)}")
    print(f"ERA5 files loaded: {len(datasets)}")
    print()

    results = []

    for _, row in df.iterrows():

        start_time = pd.Timestamp(row["start_time"])
        end_time = pd.Timestamp(row["end_time"])

        start_lat = float(row["start_latitude"])
        start_lon = float(row["start_longitude"])

        end_lat = float(row["observed_latitude"])
        end_lon = float(row["observed_longitude"])

        start_ds = find_dataset(
            datasets,
            start_lat,
            start_lon,
        )

        end_ds = find_dataset(
            datasets,
            end_lat,
            end_lon,
        )

        start_result = None
        end_result = None

        if start_ds is not None:
            start_result = extract_wind(
                start_ds,
                start_time,
                start_lat,
                start_lon,
            )

        if end_ds is not None:
            end_result = extract_wind(
                end_ds,
                end_time,
                end_lat,
                end_lon,
            )

        start_ok = (
            start_result is not None
            and start_result["available"]
        )

        end_ok = (
            end_result is not None
            and end_result["available"]
        )

        results.append(
            {
                "iceberg_id": row["iceberg_id"],
                "start_time": start_time,
                "end_time": end_time,
                "start_latitude": start_lat,
                "start_longitude": start_lon,
                "end_latitude": end_lat,
                "end_longitude": end_lon,
                "start_available": start_ok,
                "end_available": end_ok,
                "complete": start_ok and end_ok,
            }
        )

    result_df = pd.DataFrame(results)

    output = ROOT / "data/catalog/era5_calibration_coverage.csv"
    result_df.to_csv(output, index=False)

    print("ERA5 COVERAGE")
    print("=" * 50)

    print(f"Total pairs:       {len(result_df)}")
    print(
        f"Start usable:      "
        f"{result_df['start_available'].sum()}"
    )
    print(
        f"End usable:        "
        f"{result_df['end_available'].sum()}"
    )
    print(
        f"Complete pairs:    "
        f"{result_df['complete'].sum()}"
    )

    coverage = (
        result_df["complete"].mean() * 100
    )

    print(f"Coverage:          {coverage:.1f}%")

    print()
    print(f"Saved: {output}")

    for item in datasets:
        item["ds"].close()


if __name__ == "__main__":
    main()