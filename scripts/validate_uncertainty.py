import math
from pathlib import Path

import numpy as np
import pandas as pd

from drift_engine import propagate_position


BASE_DIR = Path(__file__).resolve().parents[1]

DATA_DIR = BASE_DIR / "data" / "catalog"

CALIBRATION_FILE = DATA_DIR / "calibration_dataset.csv"
COEFFICIENT_FILE = DATA_DIR / "leave_one_iceberg_out_coefficients.csv"
EVALUATION_FILE = DATA_DIR / "leave_one_iceberg_out_evaluation.csv"

OUTPUT_FILE = DATA_DIR / "uncertainty_validation.csv"

ENSEMBLE_SIZE = 100
VELOCITY_NOISE = 0.003
RANDOM_SEED = 42

EARTH_RADIUS_M = 6371008.8


def haversine_distance_m(lat1, lon1, lat2, lon2):
    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1)
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
    ensemble_size=100,
    velocity_noise=0.003,
    seed=42,
):
    base_u = (
        alpha * ocean_u
        + beta * wind_u
    )

    base_v = (
        alpha * ocean_v
        + beta * wind_v
    )

    rng = np.random.default_rng(seed)

    trajectories = []

    for member in range(ensemble_size):

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

        pred_lat, pred_lon = propagate_position(
            latitude,
            longitude,
            u,
            v,
            duration_hours
        )

        trajectories.append(
            {
                "member": member,
                "latitude": pred_lat,
                "longitude": pred_lon,
                "u": u,
                "v": v,
            }
        )

    ensemble = pd.DataFrame(trajectories)

    center_lat = ensemble["latitude"].median()
    center_lon = ensemble["longitude"].median()

    distances = []

    for _, row in ensemble.iterrows():

        distance = haversine_distance_m(
            center_lat,
            center_lon,
            row["latitude"],
            row["longitude"],
        )

        distances.append(distance)

    ensemble["distance_from_center_m"] = distances

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
        base_u,
        base_v,
    )


def main():

    print("=" * 70)
    print("UNCERTAINTY VALIDATION")
    print("=" * 70)

    calibration = pd.read_csv(
        CALIBRATION_FILE
    )

    coefficients = pd.read_csv(
        COEFFICIENT_FILE
    )

    evaluation = pd.read_csv(
        EVALUATION_FILE
    )

    print(
        f"Calibration rows : {len(calibration)}"
    )

    print(
        f"Coefficient rows : {len(coefficients)}"
    )

    print(
        f"Evaluation rows  : {len(evaluation)}"
    )

    print()

    print(
        "Calibration columns:"
    )

    print(
        list(calibration.columns)
    )

    print()

    print(
        "Coefficient columns:"
    )

    print(
        list(coefficients.columns)
    )

    print()

    print(
        "Evaluation columns:"
    )

    print(
        list(evaluation.columns)
    )

    print()

    # ---------------------------------------------------------
    # Merge fold coefficients
    # ---------------------------------------------------------

    coefficient_map = {}

    for _, row in coefficients.iterrows():

        coefficient_map[
            str(row["test_iceberg"])
        ] = {
            "alpha": float(row["alpha"]),
            "beta": float(row["beta"]),
        }

    results = []

    for _, row in calibration.iterrows():

        iceberg_id = str(
            row["iceberg_id"]
        )

        if iceberg_id not in coefficient_map:
            raise RuntimeError(
                f"No LOIO coefficients found "
                f"for iceberg {iceberg_id}"
            )

        alpha = coefficient_map[
            iceberg_id
        ]["alpha"]

        beta = coefficient_map[
            iceberg_id
        ]["beta"]

        start_lat = float(
            row["start_latitude"]
        )

        start_lon = float(
            row["start_longitude"]
        )

        observed_lat = float(
            row["observed_latitude"]
        )

        observed_lon = float(
            row["observed_longitude"]
        )

        duration_hours = float(
            row["duration_hours"]
        )

        ocean_u = float(
            row["ocean_u"]
        )

        ocean_v = float(
            row["ocean_v"]
        )

        wind_u = float(
            row["wind_u"]
        )

        wind_v = float(
            row["wind_v"]
        )

        (
            center_lat,
            center_lon,
            uncertainty_radius_m,
            base_u,
            base_v,
        ) = generate_ensemble(
            start_lat,
            start_lon,
            duration_hours,
            ocean_u,
            ocean_v,
            wind_u,
            wind_v,
            alpha,
            beta,
            ensemble_size=ENSEMBLE_SIZE,
            velocity_noise=VELOCITY_NOISE,
            seed=RANDOM_SEED,
        )

        actual_error_m = haversine_distance_m(
            center_lat,
            center_lon,
            observed_lat,
            observed_lon,
        )

        inside = (
            actual_error_m
            <= uncertainty_radius_m
        )

        results.append(
            {
                "iceberg_id": iceberg_id,
                "start_time": row["start_time"],
                "end_time": row["end_time"],
                "alpha": alpha,
                "beta": beta,
                "ensemble_size": ENSEMBLE_SIZE,
                "velocity_noise_mps": VELOCITY_NOISE,
                "center_latitude": center_lat,
                "center_longitude": center_lon,
                "observed_latitude": observed_lat,
                "observed_longitude": observed_lon,
                "uncertainty_radius_km":
                    uncertainty_radius_m / 1000,
                "actual_error_km":
                    actual_error_m / 1000,
                "inside_90pct_radius": bool(inside),
                "ocean_speed_mps": math.sqrt(
                    ocean_u ** 2
                    + ocean_v ** 2
                ),
                "wind_speed_mps": math.sqrt(
                    wind_u ** 2
                    + wind_v ** 2
                ),
            }
        )

    result_df = pd.DataFrame(results)

    result_df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    # ---------------------------------------------------------
    # Overall statistics
    # ---------------------------------------------------------

    coverage = (
        result_df[
            "inside_90pct_radius"
        ].mean()
        * 100
    )

    print("=" * 70)
    print("OVERALL RESULTS")
    print("=" * 70)

    print(
        f"Pairs evaluated       : "
        f"{len(result_df)}"
    )

    print(
        f"Empirical 90% coverage: "
        f"{coverage:.2f}%"
    )

    print(
        f"Mean radius           : "
        f"{result_df['uncertainty_radius_km'].mean():.3f} km"
    )

    print(
        f"Median radius         : "
        f"{result_df['uncertainty_radius_km'].median():.3f} km"
    )

    print(
        f"P90 radius            : "
        f"{result_df['uncertainty_radius_km'].quantile(.90):.3f} km"
    )

    print(
        f"Maximum radius        : "
        f"{result_df['uncertainty_radius_km'].max():.3f} km"
    )

    print(
        f"Mean actual error     : "
        f"{result_df['actual_error_km'].mean():.3f} km"
    )

    print(
        f"Median actual error   : "
        f"{result_df['actual_error_km'].median():.3f} km"
    )

    print()

    # ---------------------------------------------------------
    # Per iceberg
    # ---------------------------------------------------------

    print("=" * 70)
    print("COVERAGE BY ICEBERG")
    print("=" * 70)

    iceberg_summary = (
        result_df
        .groupby("iceberg_id")
        .agg(
            pairs=(
                "inside_90pct_radius",
                "count"
            ),
            covered=(
                "inside_90pct_radius",
                "sum"
            ),
            coverage_pct=(
                "inside_90pct_radius",
                lambda x: x.mean() * 100
            ),
            mean_radius_km=(
                "uncertainty_radius_km",
                "mean"
            ),
            mean_error_km=(
                "actual_error_km",
                "mean"
            ),
        )
        .reset_index()
    )

    print(
        iceberg_summary.to_string(
            index=False
        )
    )

    print()

    # ---------------------------------------------------------
    # Correlation
    # ---------------------------------------------------------

    correlation = result_df[
        [
            "uncertainty_radius_km",
            "actual_error_km",
        ]
    ].corr().iloc[0, 1]

    print("=" * 70)
    print("UNCERTAINTY / ERROR RELATIONSHIP")
    print("=" * 70)

    print(
        f"Correlation between "
        f"uncertainty radius and actual error: "
        f"{correlation:.4f}"
    )

    print()

    print(
        f"Saved results to:\n"
        f"{OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()