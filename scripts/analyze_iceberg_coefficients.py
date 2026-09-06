from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import lsq_linear


PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATASET = PROJECT_ROOT / "data" / "catalog" / "calibration_dataset.csv"

ALPHA_GLOBAL = 0.35665461385172254
BETA_GLOBAL = 0.001162614309995365


def fit_coefficients(df):
    X = np.column_stack([
        df["ocean_u"].to_numpy(),
        df["wind_u"].to_numpy(),
    ])

    y_u = df["observed_u"].to_numpy()

    result_u = lsq_linear(
        X,
        y_u,
        bounds=(0, np.inf),
    )

    alpha_u, beta_u = result_u.x

    X_v = np.column_stack([
        df["ocean_v"].to_numpy(),
        df["wind_v"].to_numpy(),
    ])

    y_v = df["observed_v"].to_numpy()

    result_v = lsq_linear(
        X_v,
        y_v,
        bounds=(0, np.inf),
    )

    alpha_v, beta_v = result_v.x

    alpha = (alpha_u + alpha_v) / 2
    beta = (beta_u + beta_v) / 2

    pred_u = alpha * df["ocean_u"].to_numpy() + beta * df["wind_u"].to_numpy()
    pred_v = alpha * df["ocean_v"].to_numpy() + beta * df["wind_v"].to_numpy()

    velocity_rmse = np.sqrt(
        np.mean(
            (pred_u - df["observed_u"].to_numpy()) ** 2
            + (pred_v - df["observed_v"].to_numpy()) ** 2
        )
    )

    return alpha, beta, velocity_rmse


def main():
    df = pd.read_csv(DATASET)

    print(f"Dataset shape: {df.shape}")
    print(f"Global alpha: {ALPHA_GLOBAL:.8f}")
    print(f"Global beta : {BETA_GLOBAL:.8f}")
    print()

    rows = []

    for iceberg_id, group in df.groupby("iceberg_id"):
        alpha, beta, velocity_rmse = fit_coefficients(group)

        rows.append(
            {
                "iceberg_id": iceberg_id,
                "samples": len(group),
                "alpha": alpha,
                "beta": beta,
                "velocity_rmse_mps": velocity_rmse,
                "alpha_minus_global": alpha - ALPHA_GLOBAL,
                "beta_minus_global": beta - BETA_GLOBAL,
            }
        )

    result = pd.DataFrame(rows).sort_values("iceberg_id")

    print("Per-iceberg coefficients:")
    print(result.to_string(index=False))

    print()
    print(
        f"Alpha range: "
        f"{result['alpha'].min():.6f} - "
        f"{result['alpha'].max():.6f}"
    )

    print(
        f"Beta range: "
        f"{result['beta'].min():.6f} - "
        f"{result['beta'].max():.6f}"
    )

    output = PROJECT_ROOT / "data" / "catalog" / "iceberg_specific_coefficients.csv"
    result.to_csv(output, index=False)

    print()
    print(f"Saved: {output}")


if __name__ == "__main__":
    main()