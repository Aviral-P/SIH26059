from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import numpy as np
from pyproj import Geod

from scripts.extract_environment import load_hycom, extract_hycom


CALIBRATION_FILE = (
    ROOT / "data" / "catalog" / "calibration_observations.csv"
)

OUTPUT_FILE = (
    ROOT / "data" / "catalog" / "hycom_sampling_audit.csv"
)

GEOD = Geod(ellps="WGS84")


def geodesic_distance_km(lat1, lon1, lat2, lon2):
    _, _, distance_m = GEOD.inv(
        lon1,
        lat1,
        lon2,
        lat2,
    )

    return abs(distance_m) / 1000.0


def find_nearest_hycom_time(ds, timestamp):
    timestamp = pd.Timestamp(timestamp)

    times = pd.to_datetime(ds["time"].values)

    differences = np.abs(
        (times - timestamp).astype("timedelta64[s]").astype(np.int64)
    )

    index = int(np.argmin(differences))

    return pd.Timestamp(times[index])


def find_nearest_hycom_grid_point(ds, lat, lon):
    lat_values = ds["lat"].values
    lon_values = ds["lon"].values

    nearest_lat_index = int(
        np.argmin(np.abs(lat_values - lat))
    )

    # HYCOM longitude can be represented as 0..360 instead of -180..180.
    hycom_lon = lon % 360

    nearest_lon_index = int(
        np.argmin(np.abs(lon_values - hycom_lon))
    )

    nearest_lat = float(
        lat_values[nearest_lat_index]
    )

    nearest_lon = float(
        lon_values[nearest_lon_index]
    )

    # Convert back to -180..180 for reporting.
    if nearest_lon > 180:
        nearest_lon_report = nearest_lon - 360
    else:
        nearest_lon_report = nearest_lon

    return nearest_lat, nearest_lon_report


def main():

    if not CALIBRATION_FILE.exists():
        raise FileNotFoundError(
            f"Calibration observations not found:\n{CALIBRATION_FILE}"
        )

    df = pd.read_csv(CALIBRATION_FILE)

    df["start_time"] = pd.to_datetime(df["start_time"])
    df["end_time"] = pd.to_datetime(df["end_time"])

    print("=" * 80)
    print("HYCOM SPATIAL + TEMPORAL SAMPLING AUDIT")
    print("=" * 80)

    print(f"\nTotal BYU pairs: {len(df)}")

    results = []

    complete_pairs = 0
    failed_pairs = 0

    for index, row in df.iterrows():

        iceberg_id = row["iceberg_id"]

        start_time = pd.Timestamp(row["start_time"])
        end_time = pd.Timestamp(row["end_time"])

        start_lat = float(row["start_latitude"])
        start_lon = float(row["start_longitude"])

        print(
            f"\n[{index + 1:3d}/{len(df)}] "
            f"{iceberg_id} "
            f"{start_time.date()} -> {end_time.date()}"
        )

        record = {
            "iceberg_id": iceberg_id,
            "start_time": start_time,
            "end_time": end_time,
            "start_latitude": start_lat,
            "start_longitude": start_lon,
            "hycom_start_available": False,
            "hycom_end_available": False,
        }

        start_ds = None
        end_ds = None

        try:

            # ----------------------------------------------------------
            # START TIME
            # ----------------------------------------------------------

            start_ds = load_hycom(start_time)

            actual_start_time = find_nearest_hycom_time(
                start_ds,
                start_time,
            )

            hycom_start_lat, hycom_start_lon = (
                find_nearest_hycom_grid_point(
                    start_ds,
                    start_lat,
                    start_lon,
                )
            )

            start_result = extract_hycom(
                start_ds,
                start_time,
                start_lat,
                start_lon,
            )

            start_offset_hours = (
                actual_start_time - start_time
            ).total_seconds() / 3600.0

            spatial_distance = geodesic_distance_km(
                start_lat,
                start_lon,
                hycom_start_lat,
                hycom_start_lon,
            )

            record.update(
                {
                    "hycom_start_available": bool(
                        start_result.get("available", False)
                    ),
                    "hycom_start_requested_time": start_time,
                    "hycom_start_actual_time": actual_start_time,
                    "hycom_start_time_offset_hours": start_offset_hours,
                    "hycom_start_latitude": hycom_start_lat,
                    "hycom_start_longitude": hycom_start_lon,
                    "hycom_start_spatial_distance_km": spatial_distance,
                    "hycom_start_u": start_result.get("u"),
                    "hycom_start_v": start_result.get("v"),
                    "hycom_start_speed": start_result.get("speed"),
                }
            )

            print(
                f"  START: available={record['hycom_start_available']} "
                f"time={actual_start_time} "
                f"offset={start_offset_hours:+.1f}h "
                f"distance={spatial_distance:.3f} km"
            )

        except Exception as exc:

            record["hycom_start_error"] = str(exc)

            print(
                f"  START: FAILED - {exc}"
            )

        finally:

            if start_ds is not None:
                try:
                    start_ds.close()
                except Exception:
                    pass

        try:

            # ----------------------------------------------------------
            # END TIME
            # ----------------------------------------------------------

            end_lat = float(row["observed_latitude"])
            end_lon = float(row["observed_longitude"])

            end_ds = load_hycom(end_time)

            actual_end_time = find_nearest_hycom_time(
                end_ds,
                end_time,
            )

            hycom_end_lat, hycom_end_lon = (
                find_nearest_hycom_grid_point(
                    end_ds,
                    end_lat,
                    end_lon,
                )
            )

            end_result = extract_hycom(
                end_ds,
                end_time,
                end_lat,
                end_lon,
            )

            end_offset_hours = (
                actual_end_time - end_time
            ).total_seconds() / 3600.0

            spatial_distance = geodesic_distance_km(
                end_lat,
                end_lon,
                hycom_end_lat,
                hycom_end_lon,
            )

            record.update(
                {
                    "hycom_end_available": bool(
                        end_result.get("available", False)
                    ),
                    "hycom_end_requested_time": end_time,
                    "hycom_end_actual_time": actual_end_time,
                    "hycom_end_time_offset_hours": end_offset_hours,
                    "hycom_end_latitude": hycom_end_lat,
                    "hycom_end_longitude": hycom_end_lon,
                    "hycom_end_spatial_distance_km": spatial_distance,
                    "hycom_end_u": end_result.get("u"),
                    "hycom_end_v": end_result.get("v"),
                    "hycom_end_speed": end_result.get("speed"),
                }
            )

            print(
                f"  END:   available={record['hycom_end_available']} "
                f"time={actual_end_time} "
                f"offset={end_offset_hours:+.1f}h "
                f"distance={spatial_distance:.3f} km"
            )

        except Exception as exc:

            record["hycom_end_error"] = str(exc)

            print(
                f"  END:   FAILED - {exc}"
            )

        finally:

            if end_ds is not None:
                try:
                    end_ds.close()
                except Exception:
                    pass

        record["complete_pair"] = (
            record["hycom_start_available"]
            and record["hycom_end_available"]
        )

        if record["complete_pair"]:
            complete_pairs += 1
        else:
            failed_pairs += 1

        results.append(record)

    result_df = pd.DataFrame(results)

    result_df.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    print("\n" + "=" * 80)
    print("OVERALL HYCOM SAMPLING RESULT")
    print("=" * 80)

    print(
        f"Total pairs:             {len(result_df)}"
    )

    print(
        f"Complete pairs:          {complete_pairs}"
    )

    print(
        f"Incomplete pairs:        {failed_pairs}"
    )

    coverage = (
        complete_pairs / len(result_df) * 100
        if len(result_df)
        else 0
    )

    print(
        f"Complete-pair coverage:  {coverage:.1f}%"
    )

    print("\n--- BY ICEBERG ---")

    iceberg_summary = (
        result_df
        .groupby("iceberg_id")["complete_pair"]
        .agg(["sum", "count"])
    )

    for iceberg_id, row in iceberg_summary.iterrows():

        complete = int(row["sum"])
        total = int(row["count"])

        print(
            f"{iceberg_id:8s} "
            f"{complete}/{total}"
        )

    print("\n--- TEMPORAL OFFSET ---")

    for column in [
        "hycom_start_time_offset_hours",
        "hycom_end_time_offset_hours",
    ]:

        if column in result_df:

            values = pd.to_numeric(
                result_df[column],
                errors="coerce",
            ).dropna()

            if len(values):

                print(
                    f"{column}: "
                    f"min={values.min():+.1f}h "
                    f"max={values.max():+.1f}h "
                    f"mean={values.mean():+.2f}h"
                )

    print("\n--- SPATIAL OFFSET ---")

    for column in [
        "hycom_start_spatial_distance_km",
        "hycom_end_spatial_distance_km",
    ]:

        if column in result_df:

            values = pd.to_numeric(
                result_df[column],
                errors="coerce",
            ).dropna()

            if len(values):

                print(
                    f"{column}: "
                    f"min={values.min():.3f} km "
                    f"max={values.max():.3f} km "
                    f"mean={values.mean():.3f} km"
                )

    print("\n--- HYCOM CURRENT SPEED ---")

    for column in [
        "hycom_start_speed",
        "hycom_end_speed",
    ]:

        if column in result_df:

            values = pd.to_numeric(
                result_df[column],
                errors="coerce",
            ).dropna()

            if len(values):

                print(
                    f"{column}: "
                    f"min={values.min():.6f} m/s "
                    f"max={values.max():.6f} m/s "
                    f"mean={values.mean():.6f} m/s"
                )

    print("\n" + "=" * 80)
    print(f"Saved audit: {OUTPUT_FILE}")
    print("=" * 80)


if __name__ == "__main__":
    main()