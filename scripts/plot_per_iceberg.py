
import pandas as pd
import matplotlib.pyplot as plt

# Load LOIO evaluation data
df = pd.read_csv("data/catalog/leave_one_iceberg_out_evaluation.csv")

# Ensure error columns are numeric
for col in ["calibrated_error_km", "baseline_error_km", "persistence_error_km"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# Average calibrated error for each held-out iceberg
summary = df.groupby("iceberg_id")["calibrated_error_km"].mean().sort_index()

# Create publication-style figure
plt.figure(figsize=(8,4.5))
bars = plt.bar(summary.index, summary.values)

plt.title("Per-Iceberg LOIO Performance", fontsize=14)
plt.xlabel("Held-out Iceberg", fontsize=11)
plt.ylabel("Mean Calibrated Error (km)", fontsize=11)
plt.grid(axis="y", alpha=0.3)

# Value labels
for bar in bars:
    h = bar.get_height()
    plt.text(bar.get_x() + bar.get_width()/2, h + 0.05,
             f"{h:.2f}", ha="center", fontsize=9)

plt.tight_layout()
plt.savefig("reports/figures/per_iceberg_rmse.png", dpi=300)
print("Saved reports/figures/per_iceberg_rmse.png")