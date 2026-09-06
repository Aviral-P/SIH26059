import math
from pathlib import Path

import numpy as np
import pandas as pd

from drift_engine import propagate_position


BASE_DIR = Path(__file__).resolve().parents[1]

DATA_DIR = BASE_DIR / "data" / "catalog"

CALIBRATION_FILE = DATA_DIR / "calibration_dataset.csv"
COEFFICIENT_FILE = (
    DATA_DIR / "leave_one_iceberg_out_coefficients.csv"
)

OUTPUT_FILE = (
    DATA_DIR / "uncertainty_sensitivity.csv"
)

ENSEMBLE_SIZE = 100
RANDOM_SEED = 42

VELOCITY_NOISE_LEVELS = [
    0.003,
    0.005,
    0.010,
    0.015,
    0.020,
    0.030,
]

EARTH_RADIUS_M = 6371008.8


def haversine_distance_m(
    lat1,
    lon1,
    lat2,
    lon2
):
    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = (
        math.sin(dlat / 2) ** 2
        +
        math.cos(lat1)
        * math.cos(lat2)
        * math.sin(dlon / 2) ** 2
    )

    return (
        2
        * EARTH_RADIUS_M
        * math.asin(math.sqrt(a))
    )


def generate_ensemble(
    latitude,
    longitude,
    duration_hours,
    ocean_u,
    ocean_v,
    wind_u,
    wind_v,
    alpha,
    beta,
    velocity_noise,
):
    base_u = (
        alpha * ocean_u
        + beta * wind_u
    )

    base_v = (
        alpha * ocean_v
        + beta * wind_v
    )

    rng = np.random.default_rng(
        RANDOM_SEED
    )

    trajectories = []

    for member in range(ENSEMBLE_SIZE):

        noise_u = rng.normal(
            0,
            velocity_noise
        )

        noise_v = rng.normal(
            0,
            velocity_noise
        )

        u = base_u + noise_u
        v = base_v + noise_v

        pred_lat, pred_lon = (
            propagate_position(
                latitude,
                longitude,
                u,
                v,
                duration_hours,
            )
        )

        trajectories.append(
            (
                pred_lat,
                pred_lon,
            )
        )

    lats = np.array(
        [x[0] for x in trajectories]
    )

    lons = np.array(
        [x[1] for x in trajectories]
    )

    center_lat = float(
        np.median(lats)
    )

    center_lon = float(
        np.median(lons)
    )

    distances = []

    for lat, lon in trajectories:

        distance = haversine_distance_m(
            center_lat,
            center_lon,
            lat,
            lon,
        )

        distances.append(distance)

    uncertainty_radius_m = float(
        np.percentile(
            distances,
            90
        )
    )

    return (
        center_lat,
        center_lon,
        uncertainty_radius_m,
    )


def main():

    print("=" * 72)
    print("UNCERTAINTY SENSITIVITY ANALYSIS")
    print("=" * 72)

    calibration = pd.read_csv(
        CALIBRATION_FILE
    )

    coefficients = pd.read_csv(
        COEFFICIENT_FILE
    )

    print(
        f"Calibration rows : {len(calibration)}"
    )

    print(
        f"LOIO coefficients : {len(coefficients)}"
    )

    coefficient_map = {}

    for _, row in coefficients.iterrows():

        coefficient_map[
            str(row["test_iceberg"])
        ] = (
            float(row["alpha"]),
            float(row["beta"]),
        )

    results = []

    for noise in VELOCITY_NOISE_LEVELS:

        print()
        print(
            f"Testing velocity noise = "
            f"{noise:.3f} m/s"
        )

        pair_results = []

        for _, row in calibration.iterrows():

            iceberg_id = str(
                row["iceberg_id"]
            )

            if iceberg_id not in coefficient_map:
                raise RuntimeError(
                    f"Missing coefficients for "
                    f"{iceberg_id}"
                )

            alpha, beta = (
                coefficient_map[iceberg_id]
            )

            (
                center_lat,
                center_lon,
                radius_m,
            ) = generate_ensemble(
                latitude=float(
                    row["start_latitude"]
                ),
                longitude=float(
                    row["start_longitude"]
                ),
                duration_hours=float(
                    row["duration_hours"]
                ),
                ocean_u=float(
                    row["ocean_u"]
                ),
                ocean_v=float(
                    row["ocean_v"]
                ),
                wind_u=float(
                    row["wind_u"]
                ),
                wind_v=float(
                    row["wind_v"]
                ),
                alpha=alpha,
                beta=beta,
                velocity_noise=noise,
            )

            actual_error_m = (
                haversine_distance_m(
                    center_lat,
                    center_lon,
                    float(
                        row["observed_latitude"]
                    ),
                    float(
                        row["observed_longitude"]
                    ),
                )
            )

            covered = (
                actual_error_m <= radius_m
            )

            pair_results.append(
                {
                    "iceberg_id": iceberg_id,
                    "actual_error_km":
                        actual_error_m / 1000,
                    "radius_km":
                        radius_m / 1000,
                    "covered": covered,
                }
            )

        pair_df = pd.DataFrame(
            pair_results
        )

        coverage = (
            pair_df["covered"].mean()
            * 100
        )

        mean_radius = (
            pair_df["radius_km"].mean()
        )

        median_radius = (
            pair_df["radius_km"].median()
        )

        p90_radius = (
            pair_df["radius_km"].quantile(
                0.90
            )
        )

        max_radius = (
            pair_df["radius_km"].max()
        )

        mean_error = (
            pair_df["actual_error_km"].mean()
        )

        median_error = (
            pair_df["actual_error_km"].median()
        )

        p90_error = (
            pair_df["actual_error_km"].quantile(
                0.90
            )
        )

        covered_count = int(
            pair_df["covered"].sum()
        )

        results.append(
            {
                "velocity_noise_mps": noise,
                "ensemble_size": ENSEMBLE_SIZE,
                "pairs": len(pair_df),
                "covered_pairs": covered_count,
                "coverage_pct": coverage,
                "mean_radius_km": mean_radius,
                "median_radius_km":
                    median_radius,
                "p90_radius_km": p90_radius,
                "max_radius_km": max_radius,
                "mean_actual_error_km":
                    mean_error,
                "median_actual_error_km":
                    median_error,
                "p90_actual_error_km":
                    p90_error,
            }
        )

        print(
            f"Coverage: "
            f"{coverage:.2f}% "
            f"({covered_count}/49)"
        )

        print(
            f"Mean radius: "
            f"{mean_radius:.3f} km"
        )

        print(
            f"Median radius: "
            f"{median_radius:.3f} km"
        )

    result_df = pd.DataFrame(
        results
    )

    result_df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print()
    print("=" * 72)
    print("SENSITIVITY SUMMARY")
    print("=" * 72)

    display_columns = [
        "velocity_noise_mps",
        "covered_pairs",
        "coverage_pct",
        "mean_radius_km",
        "median_radius_km",
        "p90_radius_km",
    ]

    print(
        result_df[
            display_columns
        ].to_string(
            index=False,
            float_format=lambda x: f"{x:.3f}"
        )
    )

    print()
    print("=" * 72)
    print("INTERPRETATION")
    print("=" * 72)

    closest = result_df.iloc[
        (
            result_df["coverage_pct"] - 90
        ).abs().argmin()
    ]

    print(
        "Closest tested coverage to 90%:"
    )

    print(
        f"  Noise       : "
        f"{closest['velocity_noise_mps']:.3f} m/s"
    )

    print(
        f"  Coverage    : "
        f"{closest['coverage_pct']:.2f}%"
    )

    print(
        f"  Mean radius : "
        f"{closest['mean_radius_km']:.3f} km"
    )

    print()
    print(
        "IMPORTANT:"
    )

    print(
        "The closest value is NOT automatically "
        "selected as the production noise level."
    )

    print(
        "This analysis is a sensitivity diagnostic "
        "only and uses the same held-out observations."
    )

    print()
    print(
        f"Saved to:\n{OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()