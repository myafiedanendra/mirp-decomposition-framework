#!/usr/bin/env python3
"""
Figure 4: destination-port inventory profiles for K = 5.

Two trajectories are drawn for each of the nine destination ports:
  - Stage 2: the Stage-2 model output (inventory s[p,t]);
  - post-Stage 3: a deterministic replay of the post-Stage-3 inventory
    balance (Appendix A, Eq. A24) with the deliveries of the committed fleet
    implied by Stage 2 (Eq. A18) and the 34 supplementary voyages of Table 7
    as fixed arrivals. The replay is NOT a re-optimization:

        s'[p,t] = min(max(s'[p,t-1] + TC[p,t] + VC[p,t] - d[p], 0), capacity[p])
        TC[p,t] = s2[p,t] - s2[p,t-1] + d[p] - so2[p,t]

Usage
  python figures/make_figure4.py
      Plots from results/figure4_k5_inventory_profiles.csv (the data behind the
      published figure).
  python figures/make_figure4.py --recompute
      Recomputes the replay from your own run outputs
      (OptionC_k5_SeaDist_Results/OptionC_k5_Inventory.csv and the
      'Schedule k=5' sheet of Stage3_SeaDist_kSweep_Charter_Schedule.xlsx),
      writes figures/figure4_k5_inventory_profiles_recomputed.csv, and plots it.

Outputs (next to this script): figure4_inventory_profiles_k5.png / .pdf
"""
import os
import sys
import csv
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PUBLISHED_CSV = os.path.join(ROOT, "results", "figure4_k5_inventory_profiles.csv")
INV_CSV = os.path.join(ROOT, "OptionC_k5_SeaDist_Results", "OptionC_k5_Inventory.csv")
SWEEP = os.path.join(ROOT, "Stage3_SeaDist_kSweep_Charter_Schedule.xlsx")

PERIOD_DAYS = 2
TOTAL_DAYS = 365
T_MAX = 183

# Port parameters (Table 1; initial inventories from Section 4.1), identical to
# supplementary_charter_milp_seadist_sweep.py.
PORTS = {
    "Bitung":         {"demand": 69822,  "capacity": 12000, "initial_stock": 1900},
    "Mamuju":         {"demand": 9021,   "capacity": 4000,  "initial_stock": 400},
    "Palu":           {"demand": 338083, "capacity": 8000,  "initial_stock": 300},
    "Kendari":        {"demand": 145158, "capacity": 12000, "initial_stock": 2000},
    "Ambon":          {"demand": 12205,  "capacity": 8000,  "initial_stock": 2000},
    "Oba":            {"demand": 80930,  "capacity": 6000,  "initial_stock": 725},
    "Celukan Bawang": {"demand": 129014, "capacity": 12000, "initial_stock": 1000},
    "Lembar":         {"demand": 61222,  "capacity": 5000,  "initial_stock": 600},
    "Sorong":         {"demand": 50551,  "capacity": 12000, "initial_stock": 2200},
}
DEST = list(PORTS)


def recompute():
    import openpyxl
    with open(INV_CSV, newline="") as fh:
        rows = list(csv.DictReader(fh))
    periods = [int(r["Period"]) for r in rows]
    days = [float(r["Day"]) for r in rows]
    s2 = {p: [float(r["s_" + p]) for r in rows] for p in DEST}
    so2 = {p: [float(r["so_" + p]) for r in rows] for p in DEST}
    dpp = {p: PORTS[p]["demand"] * PERIOD_DAYS / TOTAL_DAYS for p in DEST}

    tc = {p: {} for p in DEST}
    for p in DEST:
        for t in range(T_MAX):
            prev = PORTS[p]["initial_stock"] if t == 0 else s2[p][t - 1]
            delivery = s2[p][t] - prev + dpp[p] - so2[p][t]
            if delivery > 1e-6:
                tc[p][t] = delivery

    wb = openpyxl.load_workbook(SWEEP, data_only=True)
    sheet = list(wb["Schedule k=5"].iter_rows(values_only=True))
    ci = {h: i for i, h in enumerate(sheet[0])}
    vc = {p: {} for p in DEST}
    for r in sheet[1:]:
        if r[ci["port"]] is None:
            continue
        p, at = r[ci["port"]], int(r[ci["arrival_period"]])
        vc[p][at] = vc[p].get(at, 0.0) + float(r[ci["cargo"]])

    s3 = {p: [] for p in DEST}
    sh3 = {p: [] for p in DEST}
    for p in DEST:
        prev, cap = PORTS[p]["initial_stock"], PORTS[p]["capacity"]
        for t in range(T_MAX):
            raw = prev + tc[p].get(t, 0.0) + vc[p].get(t, 0.0) - dpp[p]
            s = min(max(raw, 0.0), cap)
            sh3[p].append(max(0.0, -raw) if -raw > 1e-6 else 0.0)
            s3[p].append(s)
            prev = s

    out = os.path.join(HERE, "figure4_k5_inventory_profiles_recomputed.csv")
    header = ["Period", "Day"]
    for p in DEST:
        header += ["Stage2_" + p, "PostStage3_" + p, "PostStage3_shortage_" + p]
    with open(out, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        for t in range(T_MAX):
            row = [periods[t], days[t]]
            for p in DEST:
                row += [s2[p][t], s3[p][t], sh3[p][t]]
            w.writerow(row)
    print("Wrote:", out)
    print(f"Residual shortage in the replay: {sum(sum(v) for v in sh3.values()):,.1f} t")
    return out


def load(path):
    with open(path, newline="") as fh:
        rows = list(csv.DictReader(fh))
    days = [float(r["Day"]) for r in rows]
    get = lambda col: [float(r[col]) for r in rows]
    return days, {p: (get("Stage2_" + p), get("PostStage3_" + p),
                      get("PostStage3_shortage_" + p)) for p in DEST}


def plot(path):
    days, data = load(path)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9.5})
    fig, axes = plt.subplots(3, 3, figsize=(12.5, 9.5), sharex=True)
    for ax, p in zip(axes.ravel(), DEST):
        s2, s3, sh = data[p]
        ax.plot(days, s2, color="#c0504d", lw=1.4, label="Stage 2")
        ax.plot(days, s3, color="#1f4e79", lw=1.4, label="Post-Stage 3")
        ax.axhline(PORTS[p]["capacity"], color="#7f7f7f", ls="--", lw=0.8)
        ax.set_title(p, fontsize=10, fontweight="bold")
        ax.grid(True, linestyle=":", alpha=0.45)
        ax.set_ylim(bottom=0)
        ax.margins(x=0.01)
        for t, x in enumerate(sh):
            if x > 1e-6:
                ax.scatter([days[t]], [0], marker="v", color="#c00000", s=45, zorder=5)
    for ax in axes[-1, :]:
        ax.set_xlabel("Planning day")
    for ax in axes[:, 0]:
        ax.set_ylabel("Inventory (t)")
    handles, labels = axes[0, 0].get_legend_handles_labels()
    handles.append(plt.Line2D([0], [0], color="#7f7f7f", ls="--", lw=0.8))
    labels.append("Silo capacity")
    handles.append(plt.Line2D([0], [0], marker="v", color="#c00000", ls="none"))
    labels.append("Residual shortage")
    fig.legend(handles, labels, loc="upper center", ncol=4, frameon=False,
               bbox_to_anchor=(0.5, 1.02))
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    png = os.path.join(HERE, "figure4_inventory_profiles_k5.png")
    fig.savefig(png, dpi=300, bbox_inches="tight")
    fig.savefig(os.path.join(HERE, "figure4_inventory_profiles_k5.pdf"), bbox_inches="tight")
    print("Wrote:", png)


if __name__ == "__main__":
    plot(recompute() if "--recompute" in sys.argv[1:] else PUBLISHED_CSV)
