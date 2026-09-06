import matplotlib.pyplot as plt

models = ["Persistence", "Baseline", "Calibrated"]
rmse = [9.181, 15.682, 8.565]

plt.figure(figsize=(6,4))
plt.bar(models, rmse)
plt.ylabel("RMSE (km)")
plt.title("LOIO RMSE Comparison")
plt.tight_layout()
plt.savefig("reports/figures/rmse_comparison.png", dpi=300)
print("Saved rmse_comparison.png")