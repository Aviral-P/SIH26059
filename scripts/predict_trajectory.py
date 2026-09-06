
from pathlib import Path

import numpy as np
import pandas as pd
from pyproj import Geod


ROOT = Path(__file__).resolve().parents[1]

INPUT_FILE = (
    ROOT / "data" / "catalog" /
    "calibration_dataset.csv"
)

COEFFICIENT_FILE = (
    ROOT / "data" / "catalog" /
    "calibrated_coefficients.csv"
)

OUTPUT_FILE = (
    ROOT / "data" / "catalog" /
    "trajectory_predictions.csv"
)

GEOD = Geod(ellps="WGS84")


def destination(lat, lon, u, v, hours):
    speed = np.sqrt(u ** 2 + v ** 2)

    if speed == 0:
        return lat, lon

    azimuth = np.degrees(
        np.arctan2(u, v)
    )

    distance_m = speed * hours * 3600.0

    lon2, lat2, _ = GEOD.fwd(
        lon,
        lat,
        azimuth,
        distance_m
    )

    return lat2, lon2


def main():

    print("=" * 70)
    print("ICEBERG TRAJECTORY PREDICTION")
    print("=" * 70)

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Calibration dataset not found:\n{INPUT_FILE}"
        )

    if not COEFFICIENT_FILE.exists():
        raise FileNotFoundError(
            f"Calibrated coefficient file not found:\n"
            f"{COEFFICIENT_FILE}"
        )

    df = pd.read_csv(INPUT_FILE)

    coefficients = pd.read_csv(
        COEFFICIENT_FILE
    )

    required_coefficient_columns = [
        "alpha",
        "beta"
    ]

    missing_coefficients = [
        column
        for column in required_coefficient_columns
        if column not in coefficients.columns
    ]

    if missing_coefficients:
        raise ValueError(
            "Missing coefficient columns: "
            f"{missing_coefficients}"
        )

    alpha = float(
        coefficients["alpha"].iloc[0]
    )

    beta = float(
        coefficients["beta"].iloc[0]
    )

    print("\nUsing calibrated coefficients:")
    print(f"alpha = {alpha:.8f}")
    print(f"beta  = {beta:.8f}")

    horizons = [
        6,
        12,
        18,
        24,
        30,
        36,
        48
    ]

    rows = []

    for _, row in df.iterrows():

        u = (
            alpha * row["ocean_u"]
            + beta * row["wind_u"]
        )

        v = (
            alpha * row["ocean_v"]
            + beta * row["wind_v"]
        )

        for hours in horizons:

            predicted_lat, predicted_lon = destination(
                row["start_latitude"],
                row["start_longitude"],
                u,
                v,
                hours
            )

            rows.append({
                "iceberg_id":
                    row["iceberg_id"],

                "start_time":
                    row["start_time"],

                "forecast_hours":
                    hours,

                "start_latitude":
                    row["start_latitude"],

                "start_longitude":
                    row["start_longitude"],

                "predicted_latitude":
                    predicted_lat,

                "predicted_longitude":
                    predicted_lon,

                "ocean_u":
                    row["ocean_u"],

                "ocean_v":
                    row["ocean_v"],

                "wind_u":
                    row["wind_u"],

                "wind_v":
                    row["wind_v"],

                "predicted_u":
                    u,

                "predicted_v":
                    v,

                "alpha":
                    alpha,

                "beta":
                    beta
            })

    output_df = pd.DataFrame(rows)

    output_df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print()
    print("=" * 70)
    print("TRAJECTORY PREDICTION COMPLETE")
    print("=" * 70)

    print(f"\nInput pairs       : {len(df)}")
    print(f"Forecast horizons : {horizons}")
    print(f"Output rows       : {len(output_df)}")

    print(f"\nSaved:")
    print(OUTPUT_FILE)

    print("\nSample predictions:")

    print(
        output_df[
            [
                "iceberg_id",
                "forecast_hours",
                "predicted_latitude",
                "predicted_longitude"
            ]
        ].head(15).to_string(index=False)
    )


if __name__ == "__main__":
    main()