#!/usr/bin/env python3
"""
Figure 2: combined direct financial expenditure of the two stages by number of
clusters K (penalties for unmet demand excluded).

Reads results/stage3_combined_summary_by_k.csv. The grey band marks K = 5 to 9,
whose differences are smaller than the remaining optimality gaps; these
configurations are not ranked, and K = 5 is the lowest OBSERVED value, not a
proven optimum.

Output (next to this script): figure2_combined_expenditure_by_k.png / .pdf
"""
import os
import csv
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(os.path.dirname(HERE), "results", "stage3_combined_summary_by_k.csv")

with open(SRC, newline="") as fh:
    rows = sorted(csv.DictReader(fh), key=lambda r: int(r["K"]))
ks = [int(r["K"]) for r in rows]
bn = [float(r["combined_financial_expenditure_rp"]) / 1e9 for r in rows]
i_min = bn.index(min(bn))
k_low, y_low = ks[i_min], bn[i_min]

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11})
fig, ax = plt.subplots(figsize=(7.4, 4.7))
ax.axvspan(4.6, 9.4, color="#d9d9d9", alpha=0.45, zorder=0, lw=0)
ax.text(7.0, 895, "K = 5 to 9: differences within\nsolver-gap scales (not ranked)",
        ha="center", va="top", fontsize=9, color="#404040")
ax.plot(ks, bn, "-o", color="#1f4e79", lw=2, ms=6, zorder=3,
        label="Combined financial expenditure")
ax.scatter([k_low], [y_low], s=170, facecolor="#c00000", edgecolor="black", zorder=5,
           label=f"Lowest observed combined\nexpenditure (K = {k_low})")
for k, y in zip(ks, bn):
    ax.annotate(f"{y:.1f}", xy=(k, y), xytext=(14, 4) if k in (2, 3, 4) else (0, -16),
                textcoords="offset points", ha="left" if k in (2, 3, 4) else "center",
                fontsize=8.5, color="#333333")
ax.set_xlabel("Number of clusters, K")
ax.set_ylabel("Combined direct financial expenditure (Rp billion)")
ax.set_xticks(range(2, 10))
ax.set_xlim(1.6, 9.6)
ax.set_ylim(480, 905)
ax.grid(True, linestyle=":", alpha=0.5)
ax.legend(frameon=False, loc="upper left", fontsize=9.5)
fig.tight_layout()
fig.savefig(os.path.join(HERE, "figure2_combined_expenditure_by_k.png"), dpi=300)
fig.savefig(os.path.join(HERE, "figure2_combined_expenditure_by_k.pdf"))
print(f"Lowest observed combined expenditure: K = {k_low}, Rp {y_low:.2f} billion")
