from pathlib import Path
import zipfile
import io
import re

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

BYU_STATS = ROOT / "data/raw/byu/stats_database_v7.1.zip"

OUTPUT = ROOT / "data/catalog/calibration_overlap_audit.csv"


# ---------------------------------------------------------
# Environmental availability
# ---------------------------------------------------------

ENVIRONMENT_WINDOWS = [
    {
        "name": "July validation",
        "start": pd.Timestamp("2023-07-21T00:00:00"),
        "end": pd.Timestamp("2023-07-24T23:59:59"),
    },
    {
        "name": "October production",
        "start": pd.Timestamp("2023-10-01T00:00:00"),
        "end": pd.Timestamp("2023-10-31T23:59:59"),
    },
]


# ---------------------------------------------------------
# BYU date parser
# ---------------------------------------------------------

def parse_byu_date(value):
    """
    BYU date format is YYYYDDD.

    Example:
        2023200 = day 200 of 2023
    """

    value = str(value)

    if not re.fullmatch(r"\d{7}", value):
        return pd.NaT

    year = int(value[:4])
    day_of_year = int(value[4:])

    try:
        return pd.Timestamp(
            year=year,
            month=1,
            day=1
        ) + pd.Timedelta(
            days=day_of_year - 1
        )

    except Exception:
        return pd.NaT


# ---------------------------------------------------------
# Load BYU statistics
# ---------------------------------------------------------

def load_byu():

    print()
    print("Loading BYU statistics database...")
    print(BYU_STATS)

    rows = []

    with zipfile.ZipFile(BYU_STATS) as z:

        csv_files = [
            name
            for name in z.namelist()
            if name.lower().endswith(".csv")
        ]

        print(
            f"CSV files found: {len(csv_files)}"
        )

        for name in csv_files:

            iceberg_id = Path(name).stem

            with z.open(name) as f:

                df = pd.read_csv(f)

            if "date" not in df.columns:
                continue

            df["timestamp"] = (
                df["date"]
                .apply(parse_byu_date)
            )

            df["iceberg_id"] = iceberg_id

            rows.append(
                df[
                    [
                        "iceberg_id",
                        "timestamp",
                        "lat",
                        "lon",
                        "date_gap",
                        "disp",
                    ]
                ]
            )

    result = pd.concat(
        rows,
        ignore_index=True
    )

    return result


# ---------------------------------------------------------
# Find environmental overlap
# ---------------------------------------------------------

def audit_overlap(df):

    results = []

    print()
    print("=" * 80)
    print("ENVIRONMENTAL / BYU OVERLAP AUDIT")
    print("=" * 80)

    print()
    print(
        f"Total BYU observations: {len(df):,}"
    )

    print(
        f"BYU time range: "
        f"{df['timestamp'].min()} -> "
        f"{df['timestamp'].max()}"
    )

    for window in ENVIRONMENT_WINDOWS:

        mask = (
            (df["timestamp"] >= window["start"])
            &
            (df["timestamp"] <= window["end"])
        )

        subset = df.loc[mask].copy()

        print()
        print("-" * 80)

        print(
            f"{window['name']}"
        )

        print(
            f"Environmental period: "
            f"{window['start']} -> {window['end']}"
        )

        print(
            f"BYU observations in window: "
            f"{len(subset):,}"
        )

        print(
            f"Unique icebergs: "
            f"{subset['iceberg_id'].nunique():,}"
        )

        if len(subset) > 0:

            print(
                f"Latitude range: "
                f"{subset['lat'].min():.3f} -> "
                f"{subset['lat'].max():.3f}"
            )

            print(
                f"Longitude range: "
                f"{subset['lon'].min():.3f} -> "
                f"{subset['lon'].max():.3f}"
            )

            print()
            print("Icebergs represented:")

            counts = (
                subset
                .groupby("iceberg_id")
                .size()
                .sort_values(ascending=False)
            )

            print(
                counts.head(20).to_string()
            )

        results.append({
            "environment_window": window["name"],
            "start": window["start"],
            "end": window["end"],
            "byu_observations": len(subset),
            "unique_icebergs": subset["iceberg_id"].nunique(),
        })

    return pd.DataFrame(results)


# ---------------------------------------------------------
# Check 24-hour successor availability
# ---------------------------------------------------------

def audit_24h_successors(df):

    print()
    print("=" * 80)
    print("24-HOUR SUCCESSOR AUDIT")
    print("=" * 80)

    usable = []

    july_start = pd.Timestamp(
        "2023-07-21T00:00:00"
    )

    july_end = pd.Timestamp(
        "2023-07-24T00:00:00"
    )

    # Only starting observations whose
    # +24h timestamp is inside our environmental
    # validation window.

    starts = df[
        (df["timestamp"] >= july_start)
        &
        (df["timestamp"] <= july_end)
    ].copy()

    print()
    print(
        f"Candidate starting observations: "
        f"{len(starts):,}"
    )

    for _, row in starts.iterrows():

        target_time = (
            row["timestamp"]
            + pd.Timedelta(hours=24)
        )

        if target_time > pd.Timestamp(
            "2023-07-24T23:59:59"
        ):
            continue

        same_track = df[
            (df["iceberg_id"] == row["iceberg_id"])
            &
            (df["timestamp"] == target_time)
        ]

        if len(same_track) == 0:
            continue

        target = same_track.iloc[0]

        usable.append({
            "iceberg_id": row["iceberg_id"],
            "start_timestamp": row["timestamp"],
            "target_timestamp": target_time,

            "start_lat": row["lat"],
            "start_lon": row["lon"],

            "target_lat": target["lat"],
            "target_lon": target["lon"],

            "date_gap": row["date_gap"],
            "disp_raw": row["disp"],
        })

    result = pd.DataFrame(usable)

    print()
    print(
        f"Usable 24h pairs: {len(result):,}"
    )

    if len(result) > 0:

        print()
        print(
            "Icebergs with usable 24h pairs:"
        )

        print(
            result["iceberg_id"]
            .value_counts()
            .to_string()
        )

        print()
        print("Pairs:")

        print(
            result.to_string(index=False)
        )

    return result


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

def main():

    df = load_byu()

    overlap = audit_overlap(df)

    successors = audit_24h_successors(df)

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    if len(successors) > 0:
        successors.to_csv(
            OUTPUT,
            index=False
        )
    else:
        pd.DataFrame().to_csv(
            OUTPUT,
            index=False
        )

    print()
    print("=" * 80)
    print("AUDIT COMPLETE")
    print("=" * 80)

    print()
    print(
        f"Saved: {OUTPUT}"
    )


if __name__ == "__main__":
    main()