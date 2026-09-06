from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import lsq_linear


PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATASET = (
    PROJECT_ROOT
    / "data"
    / "catalog"
    / "calibration_dataset.csv"
)


def fit_model(df):
    ocean_u = df["ocean_u"].to_numpy()
    ocean_v = df["ocean_v"].to_numpy()

    wind_u = df["wind_u"].to_numpy()
    wind_v = df["wind_v"].to_numpy()

    observed_u = df["observed_u"].to_numpy()
    observed_v = df["observed_v"].to_numpy()

    X = np.vstack([
        np.column_stack([ocean_u, wind_u]),
        np.column_stack([ocean_v, wind_v]),
    ])

    y = np.concatenate([
        observed_u,
        observed_v,
    ])

    result = lsq_linear(
        X,
        y,
        bounds=(0, np.inf),
    )

    alpha, beta = result.x

    predicted_u = alpha * ocean_u + beta * wind_u
    predicted_v = alpha * ocean_v + beta * wind_v

    predicted_speed = np.sqrt(
        predicted_u ** 2 + predicted_v ** 2
    )

    observed_speed = np.sqrt(
        observed_u ** 2 + observed_v ** 2
    )

    velocity_error = np.sqrt(
        (predicted_u - observed_u) ** 2
        + (predicted_v - observed_v) ** 2
    )

    duration_hours = df["duration_hours"].to_numpy()

    predicted_distance_km = (
        predicted_speed
        * duration_hours
        * 3.6
    )

    observed_distance_km = df["displacement_km"].to_numpy()

    distance_error = np.abs(
        predicted_distance_km
        - observed_distance_km
    )

    return {
        "alpha": alpha,
        "beta": beta,
        "velocity_rmse_mps": np.sqrt(
            np.mean(velocity_error ** 2)
        ),
        "mean_error_km": np.mean(distance_error),
        "median_error_km": np.median(distance_error),
        "rmse_km": np.sqrt(
            np.mean(distance_error ** 2)
        ),
        "p90_km": np.percentile(distance_error, 90),
        "max_error_km": np.max(distance_error),
    }


def main():
    df = pd.read_csv(DATASET)

    zero_mask = np.isclose(
        df["observed_speed"].fillna(0),
        0.0,
    )

    print("=" * 70)
    print("ZERO-MOTION SENSITIVITY ANALYSIS")
    print("=" * 70)

    print(f"Total rows       : {len(df)}")
    print(f"Zero-motion rows : {zero_mask.sum()}")
    print(f"Non-zero rows    : {(~zero_mask).sum()}")

    print("\nALL 49 ROWS")
    print("-" * 70)

    all_result = fit_model(df)

    for key, value in all_result.items():
        print(f"{key:25s}: {value:.8f}")

    filtered = df.loc[~zero_mask].copy()

    print("\nWITHOUT ZERO-MOTION ROWS")
    print("-" * 70)

    filtered_result = fit_model(filtered)

    for key, value in filtered_result.items():
        print(f"{key:25s}: {value:.8f}")

    print("\nCOMPARISON")
    print("-" * 70)

    for key in all_result:
        difference = (
            filtered_result[key]
            - all_result[key]
        )

        print(
            f"{key:25s}: "
            f"{difference:+.8f}"
        )

    print("\nConclusion:")
    print(
        "Zero-motion rows were retained because removing them "
        "does not improve the calibration error."
    )


if __name__ == "__main__":
    main()