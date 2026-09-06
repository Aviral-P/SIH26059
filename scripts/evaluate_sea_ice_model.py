from pathlib import Path
import numpy as np
import pandas as pd
from scipy.optimize import lsq_linear
from pyproj import Geod


PROJECT_ROOT = Path(__file__).resolve().parent.parent

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "catalog"
    / "calibration_dataset_sea_ice.csv"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "catalog"
    / "sea_ice_loio_evaluation.csv"
)

GEOD = Geod(ellps="WGS84")


def fit_coefficients(df):
    """
    Fit:

        u_ice = alpha * ocean_u + beta * wind_u
        v_ice = alpha * ocean_v + beta * wind_v

    Sea ice is used as a multiplicative attenuation term:

        effective_current = ocean * (1 - gamma * ice)

    Therefore:

        u_ice = alpha * ocean_u * (1 - gamma * ice)
              + beta * wind_u

    and similarly for v.

    Parameters:
        alpha >= 0
        beta >= 0
        gamma constrained to [0, 1]
    """

    ocean_u = df["ocean_u"].to_numpy(dtype=float)
    ocean_v = df["ocean_v"].to_numpy(dtype=float)

    wind_u = df["wind_u"].to_numpy(dtype=float)
    wind_v = df["wind_v"].to_numpy(dtype=float)

    ice = df["sea_ice_concentration"].to_numpy(dtype=float)

    # Three coefficients:
    # alpha
    # beta
    # gamma
    #
    # Because alpha * (1 - gamma * ice) is nonlinear
    # in alpha and gamma, use a small grid over gamma
    # and solve alpha/beta by constrained least squares.

    best = None

    for gamma in np.linspace(0.0, 1.0, 101):

        effective_u = ocean_u * (1.0 - gamma * ice)
        effective_v = ocean_v * (1.0 - gamma * ice)

        X = np.vstack(
            [
                np.concatenate([effective_u, effective_v]),
                np.concatenate([wind_u, wind_v]),
            ]
        ).T

        y = np.concatenate(
            [
                df["observed_u"].to_numpy(dtype=float),
                df["observed_v"].to_numpy(dtype=float),
            ]
        )

        result = lsq_linear(
            X,
            y,
            bounds=(
                [0.0, 0.0],
                [np.inf, np.inf],
            ),
        )

        if best is None or result.cost < best["cost"]:
            best = {
                "alpha": float(result.x[0]),
                "beta": float(result.x[1]),
                "gamma": float(gamma),
                "cost": float(result.cost),
            }

    return best


def predict(df, alpha, beta, gamma):
    ice = df["sea_ice_concentration"].to_numpy(dtype=float)

    effective_u = (
        df["ocean_u"].to_numpy(dtype=float)
        * (1.0 - gamma * ice)
    )

    effective_v = (
        df["ocean_v"].to_numpy(dtype=float)
        * (1.0 - gamma * ice)
    )

    pred_u = (
        alpha * effective_u
        + beta * df["wind_u"].to_numpy(dtype=float)
    )

    pred_v = (
        alpha * effective_v
        + beta * df["wind_v"].to_numpy(dtype=float)
    )

    return pred_u, pred_v


def geodesic_error(row, pred_u, pred_v):
    duration_seconds = (
        float(row["duration_hours"]) * 3600.0
    )

    pred_distance_m = (
        np.sqrt(pred_u**2 + pred_v**2)
        * duration_seconds
    )

    pred_speed = np.sqrt(
        pred_u**2 + pred_v**2
    )

    if pred_speed == 0:
        pred_lat = row["start_latitude"]
        pred_lon = row["start_longitude"]
    else:
        azimuth = np.degrees(
            np.arctan2(pred_u, pred_v)
        )

        pred_lon, pred_lat, _ = GEOD.fwd(
            row["start_longitude"],
            row["start_latitude"],
            azimuth,
            pred_distance_m,
        )

    _, _, error_m = GEOD.inv(
        pred_lon,
        pred_lat,
        row["observed_longitude"],
        row["observed_latitude"],
    )

    return error_m / 1000.0


def main():

    print("=" * 70)
    print("SEA-ICE MODEL — LEAVE-ONE-ICEBERG-OUT")
    print("=" * 70)

    df = pd.read_csv(INPUT_FILE)

    print(f"Rows: {len(df)}")

    icebergs = sorted(
        df["iceberg_id"].unique()
    )

    print(f"Icebergs: {len(icebergs)}")
    print()

    results = []

    for test_iceberg in icebergs:

        train = df[
            df["iceberg_id"] != test_iceberg
        ].copy()

        test = df[
            df["iceberg_id"] == test_iceberg
        ].copy()

        params = fit_coefficients(train)

        alpha = params["alpha"]
        beta = params["beta"]
        gamma = params["gamma"]

        print(
            f"{test_iceberg}: "
            f"alpha={alpha:.6f}, "
            f"beta={beta:.6f}, "
            f"gamma={gamma:.2f}"
        )

        pred_u, pred_v = predict(
            test,
            alpha,
            beta,
            gamma,
        )

        for i, (_, row) in enumerate(
            test.iterrows()
        ):

            calibrated_error = geodesic_error(
                row,
                pred_u[i],
                pred_v[i],
            )

            # Persistence baseline.
            persistence_error = float(
                row["displacement_km"]
            )

            results.append(
                {
                    "test_iceberg": test_iceberg,
                    "iceberg_id": test_iceberg,
                    "start_time": row["start_time"],
                    "persistence_error_km": persistence_error,
                    "sea_ice_model_error_km": calibrated_error,
                    "alpha": alpha,
                    "beta": beta,
                    "gamma": gamma,
                    "sea_ice_concentration": row[
                        "sea_ice_concentration"
                    ],
                }
            )

    result_df = pd.DataFrame(results)

    result_df.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    print()
    print("=" * 70)
    print("OVERALL RESULTS")
    print("=" * 70)

    persistence = result_df[
        "persistence_error_km"
    ]

    sea_ice = result_df[
        "sea_ice_model_error_km"
    ]

    print(
        f"Persistence mean : "
        f"{persistence.mean():.4f} km"
    )

    print(
        f"Sea-ice mean     : "
        f"{sea_ice.mean():.4f} km"
    )

    print(
        f"Persistence RMSE : "
        f"{np.sqrt(np.mean(persistence**2)):.4f} km"
    )

    print(
        f"Sea-ice RMSE     : "
        f"{np.sqrt(np.mean(sea_ice**2)):.4f} km"
    )

    mean_skill = (
        1
        - sea_ice.mean()
        / persistence.mean()
    )

    rmse_skill = (
        1
        - np.sqrt(np.mean(sea_ice**2))
        / np.sqrt(np.mean(persistence**2))
    )

    print(
        f"Mean skill       : "
        f"{mean_skill * 100:.2f}%"
    )

    print(
        f"RMSE skill       : "
        f"{rmse_skill * 100:.2f}%"
    )

    print()
    print("Per iceberg:")

    summary = (
        result_df
        .groupby("iceberg_id")
        .agg(
            persistence_mean=(
                "persistence_error_km",
                "mean",
            ),
            sea_ice_mean=(
                "sea_ice_model_error_km",
                "mean",
            ),
            persistence_rmse=(
                "persistence_error_km",
                lambda x: np.sqrt(
                    np.mean(x**2)
                ),
            ),
            sea_ice_rmse=(
                "sea_ice_model_error_km",
                lambda x: np.sqrt(
                    np.mean(x**2)
                ),
            ),
        )
    )

    summary["mean_skill_pct"] = (
        1
        - summary["sea_ice_mean"]
        / summary["persistence_mean"]
    ) * 100

    summary["rmse_skill_pct"] = (
        1
        - summary["sea_ice_rmse"]
        / summary["persistence_rmse"]
    ) * 100

    print(summary.to_string())

    print()
    print(f"Saved: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()