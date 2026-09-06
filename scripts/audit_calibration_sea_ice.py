from pathlib import Path
import sys
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.sea_ice_service import get_sea_ice


INPUT_FILE = PROJECT_ROOT / "data" / "catalog" / "calibration_dataset.csv"
OUTPUT_FILE = PROJECT_ROOT / "data" / "catalog" / "calibration_sea_ice_audit.csv"


def nearest_cell(cells, latitude, longitude):
    if not cells:
        return None

    best = None
    best_distance = float("inf")

    for cell in cells:
        dlat = cell["latitude"] - latitude
        dlon = cell["longitude"] - longitude

        # Approximate local distance in degrees.
        distance = np.sqrt(dlat**2 + dlon**2)

        if distance < best_distance:
            best_distance = distance
            best = cell

    if best is None:
        return None

    return {
        "concentration": best["concentration"],
        "distance_deg": best_distance,
    }


def main():
    print("=" * 70)
    print("CALIBRATION SEA-ICE COVERAGE AUDIT")
    print("=" * 70)

    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Missing input file: {INPUT_FILE}")

    df = pd.read_csv(INPUT_FILE)

    print(f"Input rows: {len(df)}")
    print(f"Input file: {INPUT_FILE}")
    print()

    results = []

    for i, row in df.iterrows():

        iceberg_id = row["iceberg_id"]
        timestamp = row["start_time"]
        latitude = float(row["start_latitude"])
        longitude = float(row["start_longitude"])

        print(
            f"[{i + 1:02d}/{len(df)}] "
            f"{iceberg_id} | {timestamp} | "
            f"({latitude:.4f}, {longitude:.4f})",
            flush=True,
        )

        try:
            cells = get_sea_ice(
                min_lat=latitude - 0.25,
                max_lat=latitude + 0.25,
                min_lon=longitude - 0.25,
                max_lon=longitude + 0.25,
                date=timestamp,
            )

            nearest = nearest_cell(
                cells,
                latitude,
                longitude,
            )

            if nearest is None:
                results.append(
                    {
                        "iceberg_id": iceberg_id,
                        "start_time": timestamp,
                        "latitude": latitude,
                        "longitude": longitude,
                        "cell_count": 0,
                        "sea_ice_concentration": np.nan,
                        "nearest_distance_deg": np.nan,
                        "status": "NO_CELLS",
                    }
                )

                print("    -> NO CELLS", flush=True)

            else:
                concentration = nearest["concentration"]

                results.append(
                    {
                        "iceberg_id": iceberg_id,
                        "start_time": timestamp,
                        "latitude": latitude,
                        "longitude": longitude,
                        "cell_count": len(cells),
                        "sea_ice_concentration": concentration,
                        "nearest_distance_deg": nearest["distance_deg"],
                        "status": "OK",
                    }
                )

                print(
                    f"    -> cells={len(cells)}, "
                    f"concentration={concentration:.3f}, "
                    f"distance={nearest['distance_deg']:.5f} deg",
                    flush=True,
                )

        except Exception as e:

            results.append(
                {
                    "iceberg_id": iceberg_id,
                    "start_time": timestamp,
                    "latitude": latitude,
                    "longitude": longitude,
                    "cell_count": 0,
                    "sea_ice_concentration": np.nan,
                    "nearest_distance_deg": np.nan,
                    "status": f"ERROR: {type(e).__name__}: {e}",
                }
            )

            print(
                f"    -> ERROR: {type(e).__name__}: {e}",
                flush=True,
            )

    result_df = pd.DataFrame(results)

    result_df.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)

    total = len(result_df)

    ok = (result_df["status"] == "OK").sum()
    no_cells = (result_df["status"] == "NO_CELLS").sum()
    errors = (~result_df["status"].isin(["OK", "NO_CELLS"])).sum()

    print(f"Total observations : {total}")
    print(f"With sea ice       : {ok}")
    print(f"Without cells      : {no_cells}")
    print(f"Errors             : {errors}")

    valid = result_df[
        result_df["sea_ice_concentration"].notna()
    ]

    if len(valid) > 0:
        print()
        print("Sea-ice concentration:")
        print(f"  Mean   : {valid['sea_ice_concentration'].mean():.4f}")
        print(f"  Median : {valid['sea_ice_concentration'].median():.4f}")
        print(f"  Min    : {valid['sea_ice_concentration'].min():.4f}")
        print(f"  Max    : {valid['sea_ice_concentration'].max():.4f}")

    print()
    print("Coverage by iceberg:")

    coverage = (
        result_df
        .groupby("iceberg_id")
        .agg(
            observations=("iceberg_id", "size"),
            valid=("sea_ice_concentration", lambda x: x.notna().sum()),
        )
    )

    coverage["coverage_pct"] = (
        coverage["valid"]
        / coverage["observations"]
        * 100
    )

    print(coverage.to_string())

    print()
    print(f"Saved: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()