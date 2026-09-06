from pathlib import Path
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

INPUT = ROOT / "data/processed/calibration_data.csv"
OUTPUT = ROOT / "data/catalog/calibration_pairs.csv"


def main():

    print("=" * 80)
    print("BUILDING 24-HOUR CALIBRATION PAIRS")
    print("=" * 80)

    df = pd.read_csv(INPUT)

    df["date"] = pd.to_datetime(df["date"])

    df = df.sort_values(
        ["iceberg_id", "date"]
    ).reset_index(drop=True)

    pairs = []

    for iceberg_id, group in df.groupby("iceberg_id"):

        group = group.sort_values("date").reset_index(drop=True)

        for i in range(len(group) - 1):

            start = group.iloc[i]
            target = group.iloc[i + 1]

            time_gap = (
                target["date"] - start["date"]
            ).total_seconds() / 3600

            if time_gap != 24:
                continue

            pairs.append(
                {
                    "iceberg_id": iceberg_id,

                    "start_time": start["date"],
                    "target_time": target["date"],

                    "start_lat": start["lat"],
                    "start_lon": start["lon"],

                    "target_lat": target["lat"],
                    "target_lon": target["lon"],

                    "date_gap": start["date_gap"],
                    "disp_raw": start["disp"],

                    "mask": start["mask"],
                    "flags": start["flags"],
                }
            )

    result = pd.DataFrame(pairs)

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    result.to_csv(
        OUTPUT,
        index=False
    )

    print()
    print("Pairs:", len(result))
    print(
        "Icebergs:",
        result["iceberg_id"].nunique()
    )

    print()
    print("Pairs per iceberg:")

    print(
        result.groupby("iceberg_id")
        .size()
        .to_string()
    )

    print()
    print("Time gaps:")

    print(
        (
            pd.to_datetime(result["target_time"])
            - pd.to_datetime(result["start_time"])
        )
        .dt.total_seconds()
        .div(3600)
        .value_counts()
        .sort_index()
        .to_string()
    )

    print()
    print("Saved:", OUTPUT)


if __name__ == "__main__":
    main()