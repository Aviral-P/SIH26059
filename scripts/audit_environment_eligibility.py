from pathlib import Path
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

INPUT = (
    ROOT
    / "data/catalog/calibration_overlap_audit.csv"
)


# ---------------------------------------------------------
# Common spatial coverage
# ---------------------------------------------------------

# Conservative intersection of the historical
# ERA5 + HYCOM validation domains.

MIN_LAT = -67.0
MAX_LAT = -60.0

MIN_LON = -50.0
MAX_LON = -44.0


def main():

    df = pd.read_csv(INPUT)

    print()
    print("=" * 80)
    print("ENVIRONMENTAL SPATIAL ELIGIBILITY AUDIT")
    print("=" * 80)

    print()
    print(
        f"Input pairs: {len(df):,}"
    )

    print()
    print("Common environmental domain:")
    print(
        f"Latitude : {MIN_LAT} -> {MAX_LAT}"
    )
    print(
        f"Longitude: {MIN_LON} -> {MAX_LON}"
    )

    # -----------------------------------------------------
    # Starting-point eligibility
    # -----------------------------------------------------

    start_inside = (
        (df["start_lat"] >= MIN_LAT)
        & (df["start_lat"] <= MAX_LAT)
        & (df["start_lon"] >= MIN_LON)
        & (df["start_lon"] <= MAX_LON)
    )

    # -----------------------------------------------------
    # Target-point eligibility
    # -----------------------------------------------------

    target_inside = (
        (df["target_lat"] >= MIN_LAT)
        & (df["target_lat"] <= MAX_LAT)
        & (df["target_lon"] >= MIN_LON)
        & (df["target_lon"] <= MAX_LON)
    )

    # Require BOTH endpoints to be inside.
    # This is stricter and safer for calibration.

    eligible = df[
        start_inside & target_inside
    ].copy()

    print()
    print(
        f"Starting points inside domain: "
        f"{start_inside.sum():,}"
    )

    print(
        f"Target points inside domain: "
        f"{target_inside.sum():,}"
    )

    print(
        f"Pairs with BOTH endpoints inside: "
        f"{len(eligible):,}"
    )

    print()
    print(
        f"Unique eligible icebergs: "
        f"{eligible['iceberg_id'].nunique():,}"
    )

    # -----------------------------------------------------
    # List eligible tracks
    # -----------------------------------------------------

    if len(eligible) > 0:

        print()
        print("Eligible icebergs:")
        print(
            eligible["iceberg_id"]
            .value_counts()
            .to_string()
        )

        print()
        print("Eligible pairs:")
        print(
            eligible.to_string(index=False)
        )

    # -----------------------------------------------------
    # Save
    # -----------------------------------------------------

    output = (
        ROOT
        / "data/catalog/environment_eligible_pairs.csv"
    )

    output.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    eligible.to_csv(
        output,
        index=False
    )

    print()
    print("=" * 80)
    print("AUDIT COMPLETE")
    print("=" * 80)

    print()
    print(
        f"Saved: {output}"
    )


if __name__ == "__main__":
    main()