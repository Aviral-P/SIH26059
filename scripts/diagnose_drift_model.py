from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent

CALIBRATION_FILE = (
    PROJECT_ROOT
    / "data"
    / "catalog"
    / "calibration_dataset.csv"
)

LOIO_FILE = (
    PROJECT_ROOT
    / "data"
    / "catalog"
    / "leave_one_iceberg_out_evaluation.csv"
)


def print_section(title):
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


def main():
    calibration = pd.read_csv(CALIBRATION_FILE)
    loio = pd.read_csv(LOIO_FILE)

    print_section("DATASET OVERVIEW")

    print(f"Calibration shape: {calibration.shape}")
    print(f"LOIO shape: {loio.shape}")

    print(
        "Icebergs:",
        sorted(calibration["iceberg_id"].dropna().unique())
    )

    print(
        "Samples per iceberg:"
    )
    print(
        calibration.groupby("iceberg_id").size().to_string()
    )

    print_section("OBSERVED MOTION")

    print(
        calibration[
            [
                "observed_speed",
                "observed_u",
                "observed_v",
                "displacement_km",
            ]
        ].describe().to_string()
    )

    print_section("ENVIRONMENTAL VARIABLES")

    print(
        calibration[
            [
                "ocean_speed",
                "wind_speed",
                "temperature",
                "wave_height",
            ]
        ].describe().to_string()
    )

    print_section("ZERO / NEAR-ZERO MOTION")

    speed = calibration["observed_speed"].fillna(0)

    zero_rows = calibration[np.isclose(speed, 0.0)]
    near_zero_rows = calibration[speed < 0.005]

    print(f"Exact zero observed speed: {len(zero_rows)}")
    print(f"Near-zero observed speed : {len(near_zero_rows)}")

    if len(zero_rows):
        print(
            zero_rows[
                [
                    "iceberg_id",
                    "start_time",
                    "end_time",
                    "observed_u",
                    "observed_v",
                    "observed_speed",
                    "displacement_km",
                    "ocean_speed",
                    "wind_speed",
                ]
            ].to_string(index=False)
        )

    print_section("LOIO ERROR SUMMARY")

    for column in [
        "persistence_error_km",
        "baseline_error_km",
        "calibrated_error_km",
    ]:
        if column in loio.columns:
            values = loio[column].dropna()

            print(f"\n{column}")
            print(f"mean   : {values.mean():.4f}")
            print(f"median : {values.median():.4f}")
            print(f"std    : {values.std():.4f}")
            print(f"min    : {values.min():.4f}")
            print(f"max    : {values.max():.4f}")

    print_section("LOIO ERROR BY ICEBERG")

    if "test_iceberg" in loio.columns:
        grouped = (
            loio.groupby("test_iceberg")["calibrated_error_km"]
            .agg(
                mean="mean",
                median="median",
                max="max",
            )
            .sort_index()
        )

        print(grouped.to_string())

    print_section("CORRELATION WITH OBSERVED SPEED")

    numeric_columns = [
        "ocean_speed",
        "wind_speed",
        "temperature",
        "wave_height",
    ]

    for column in numeric_columns:
        if column not in calibration.columns:
            continue

        valid = calibration[[column, "observed_speed"]].dropna()

        if len(valid) < 2:
            print(f"{column}: insufficient data")
            continue

        correlation = valid[column].corr(valid["observed_speed"])

        print(
            f"{column:20s}: "
            f"{correlation:.4f}"
        )

    print_section("ICEBERG ENVIRONMENTAL MEANS")

    grouped = (
        calibration.groupby("iceberg_id")[
            [
                "observed_speed",
                "ocean_speed",
                "wind_speed",
            ]
        ]
        .mean()
        .sort_index()
    )

    print(grouped.to_string())

    print_section("MISSING / NON-FINITE VALUES")

    numeric = calibration.select_dtypes(include=[np.number])

    missing = numeric.isna().sum()
    nonfinite = (~np.isfinite(numeric)).sum()

    print("Missing values:")
    print(missing[missing > 0].to_string())

    print("\nNon-finite values:")
    print(nonfinite[nonfinite > 0].to_string())


if __name__ == "__main__":
    main()