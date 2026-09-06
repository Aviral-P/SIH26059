
import matplotlib.pyplot as plt

labels = ["Candidate", "HYCOM", "ERA5", "Both"]
values = [105, 63, 91, 49]

plt.figure(figsize=(7,4.5))
bars = plt.bar(labels, values)

plt.ylabel("Available Pairs", fontsize=11)
plt.title("Environmental Data Coverage", fontsize=14)
plt.grid(axis="y", alpha=0.3)

# Add value labels
for bar in bars:
    h = bar.get_height()
    plt.text(bar.get_x()+bar.get_width()/2,
             h+1,
             str(int(h)),
             ha="center",
             fontsize=10)

plt.tight_layout()
plt.savefig("reports/figures/environment_coverage.png", dpi=300)
print("Saved reports/figures/environment_coverage.png")