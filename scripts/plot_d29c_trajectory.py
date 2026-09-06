
import pandas as pd
import matplotlib.pyplot as plt

# Load trajectory predictions
df = pd.read_csv("data/catalog/trajectory_predictions.csv")

# Filter D29C
d29 = df[df["iceberg_id"].str.lower() == "d29c"].copy()

# Keep only the main presentation horizons
d29 = d29[d29["forecast_hours"].isin([6,12,24,48])]
d29 = d29.sort_values(["start_time","forecast_hours"])

plt.figure(figsize=(7,7))

# Plot observed starting locations
plt.scatter(
    d29["start_longitude"],
    d29["start_latitude"],
    s=45,
    label="Observed Start"
)

# Plot predicted locations
plt.plot(
    d29["predicted_longitude"],
    d29["predicted_latitude"],
    marker="o",
    linewidth=2,
    markersize=5,
    label="Predicted Drift"
)

# Label forecast horizons
for _, row in d29.iterrows():
    plt.text(
        row["predicted_longitude"]+0.01,
        row["predicted_latitude"]+0.01,
        f'{int(row["forecast_hours"])}h',
        fontsize=8
    )

plt.xlabel("Longitude", fontsize=11)
plt.ylabel("Latitude", fontsize=11)
plt.title("D29C Iceberg: Observed vs Predicted Drift", fontsize=14)
plt.grid(alpha=0.3)
plt.legend()
plt.tight_layout()

plt.savefig("reports/figures/d29c_trajectory.png", dpi=300)
print("Saved reports/figures/d29c_trajectory.png")
