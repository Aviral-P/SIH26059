

import pandas as pd
import matplotlib.pyplot as plt

# Load uncertainty data
df = pd.read_csv("data/catalog/uncertainty_envelope.csv")

# Find the forecast horizon column automatically
forecast_col = next(c for c in df.columns if "forecast" in c.lower() or "hour" in c.lower())

# Find P50, P80, P90 and P95 columns automatically
targets = ["50", "80", "90", "95"]
curves = []

for t in targets:
    match = next((c for c in df.columns if t in c.lower()), None)
    if match:
        curves.append((match, f"P{t}"))

plt.figure(figsize=(7,4.5))

for col, label in curves:
    df[col] = pd.to_numeric(df[col], errors="coerce")
    plt.plot(df[forecast_col], df[col], marker="o", linewidth=2, markersize=5, label=label)

plt.xlabel("Forecast Horizon (hours)", fontsize=11)
plt.ylabel("Error Radius (km)", fontsize=11)
plt.title("Forecast Uncertainty Envelope", fontsize=14)
plt.grid(alpha=0.3)
plt.legend()
plt.tight_layout()

plt.savefig("reports/figures/uncertainty_envelope.png", dpi=300)
print("Saved reports/figures/uncertainty_envelope.png")