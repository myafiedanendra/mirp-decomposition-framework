# Maritime Inventory Routing with Time-Charter Fleet Sizing and Supplementary Voyage Chartering

Code, public model inputs and reported results for the article

> Danendra, Maulana Yafie, Arimbi Sujono, and Siti Dwi Lazuardi. *Maritime Inventory Routing with Time-Charter Fleet Sizing and Supplementary Voyage Chartering for Bulk Cement Distribution.* Submitted to *Maritime Policy & Management*.
> [Citation details to be completed after publication.]

## What the framework does

The repository implements a sequential three-stage decision-support framework for a one-to-many maritime inventory routing problem (MIRP). The case is one production port (Biringkassi) and nine consumption ports in Indonesia, with eight candidate self-unloading cement carriers identified as CC1 to CC8.

| Stage | Script | What it does |
|---|---|---|
| 1 | `mirp_option_c_seadist.py` | K-Means clustering of the destination ports (k-means++, 20 restarts, seed 42). The visit sequence of each cluster is then found by complete enumeration over the **maritime sailing-distance matrix**. |
| 2 | `mirp_option_c_seadist.py` | Time-indexed MILP over 2-day periods (183 periods, 366 modeled days). It selects the **time-charter fleet endogenously** and jointly determines cluster assignment, voyage scheduling, cargo allocation and destination-silo inventory. Unmet demand is penalized. |
| 3 | `supplementary_charter_milp_seadist_sweep.py` | Inventory-aware MILP for **supplementary voyage chartering**. Uncommitted vessels make direct voyages for the demand left unserved by the committed fleet, while silo capacities are respected period by period. |

**Key modeling points:**

- **Sequential design.** The time-charter fleet is fixed in Stage 2 before supplementary voyage charters are deployed in Stage 3. The two layers are not optimized jointly.
- **Distances.** All sailing times and voyage costs come from the maritime sailing-distance matrix in `data/sea_distance_matrix_nm.csv` (Table A5 of the supplementary appendix). The values are used exactly as recorded.
- **Expenditure.** Direct financial expenditure excludes the penalties for unmet demand in both stages.
- **Supplementary charter cost.** This is a modeled time-charter-equivalent proxy (θ = 1), not an observed voyage-charter freight rate. Supplementary vessels are assumed to be available whenever they are deployed.
- **Cargo-space utilization** of the deployed time-charter voyages is a reporting quantity, not a term in the objective.

### Reported results in brief

The full tables are in `results/`.

- **Committed fleet size.** Configurations with K = 5 to 9 clusters each commit two time-chartered vessels.
- **K = 5.** The five-cluster configuration gave the lowest observed combined direct financial expenditure, Rp 534.74 billion. Its Stage-2 and Stage-3 solutions reached their time limits, with gaps of about 3.41% and 4.13%.
- **No ranking within K = 5 to 9.** The differences among K = 5 to 9 are smaller than the remaining optimality gaps. These configurations are therefore **not ranked**, and K = 5 is not a proven optimal number of clusters.
- **Stage 3 for K = 5.** Thirty-four supplementary voyages (CC4, CC6, CC8) reduce the Stage-2 shortage from about 111,284 t to a residual of about 1,766 t, a reduction of about 98.4%. **Stage 3 does not remove all shortage**: a residual remains at the boundaries of the horizon.

## Repository structure

```
.
├── README.md                                  this file
├── LICENSE                                    MIT licence (code)
├── requirements.txt                           Python dependencies
├── mirp_option_c_seadist.py                   Stages 1 and 2
├── supplementary_charter_milp_seadist_sweep.py  Stage 3 (K = 2..9)
├── run_seadist_ksweep.py                      runs Stages 1-2 for K = 2..9
├── data/
│   ├── sea_distance_matrix_nm.csv             maritime sailing distances (nm), Table A5
│   ├── sea_distance_matrix_nm.meta.json       checksums and value policy
│   ├── ports.csv                              port parameters (Table 1, Section 4.1, A.4)
│   ├── vessels.csv                            CC1-CC8 specifications (Table 2, Table A4)
│   ├── parameters.csv                         scalar cost, time and solver parameters
│   └── port_coordinates.template.csv          template only (see "Port coordinates")
├── results/
│   ├── stage1_clusters_by_k.csv               clusters, visit sequences, sea round trips
│   ├── stage2_summary_by_k.csv                Table 5 plus Stage-2 cost components
│   ├── stage3_combined_summary_by_k.csv       Table 6
│   ├── stage3_vc_schedule_k5.csv              Table 7 (supplementary voyages, K = 5)
│   └── figure4_k5_inventory_profiles.csv      data behind Figure 4
├── figures/
│   ├── make_figure2.py                        redraws Figure 2 from results/
│   └── make_figure4.py                        redraws Figure 4 from results/ (or from a re-run)
├── docs/reproducibility_notes.md              environment, solver behavior, checks
├── REPOSITORY_CHANGE_LOG.md                   what changed from the earlier repository
├── REPOSITORY_RELEASE_CHECKLIST.md            pre-release checks
└── SHA256SUMS.txt                             checksums of all files in this release
```

The model parameters are written into the two model scripts. The CSV files in `data/` (other than the distance matrix) document the same values in tabular form, to match the article. The scripts do not read them.

## Software environment

- Python 3.12. The reported runs used Python 3.12.7.
- Gurobi Optimizer **12.0.1** with a valid licence (free academic licences are available). Stage 3 requires Gurobi. Stage 2 has an OR-Tools fallback, which was **not** used for the reported results.
- `pip install -r requirements.txt`
- Reference machine for the reported runs:
  - AMD Ryzen 3 5300U, 16 GB RAM, Windows 11;
  - Gurobi `Threads = 0` (all cores);
  - time limits of 7,200 s (Stage 2) and 1,200 s (Stage 3), relative MIP gap 2%.

## Execution order

```bash
pip install -r requirements.txt

# Stages 1 and 2 for all configurations (about 8 x 2 h of solver time)
python run_seadist_ksweep.py

# or a single configuration
K_CLUSTERS=5 python mirp_option_c_seadist.py

# Stage 3 for K = 2..9 (needs all eight Stage-2 result folders)
python supplementary_charter_milp_seadist_sweep.py
```

**Outputs:**

- Stage 2 writes `OptionC_k{K}_SeaDist_Results/`: report, schedule, inventory, itinerary workbook and run manifest.
- Stage 3 writes `Stage3_SeaDist_kSweep_Charter_Schedule.xlsx` and `Stage3_SeaDist_run_manifest.json`.
- `python figures/make_figure2.py` and `python figures/make_figure4.py` redraw Figures 2 and 4 from `results/`. Add `--recompute` to the Figure 4 script to rebuild its data from your own run.

No script overwrites existing output. Compare the new outputs with the files in `results/`. `docs/reproducibility_notes.md` explains why time-limited runs may not reproduce the K = 5 to 9 incumbents exactly.

### Port coordinates

Stage 1 clusters the ports on latitude and longitude. The coordinates are not among the parameters reported in the article, so they are **not distributed** here.

- **Without coordinates (default):** the Stage-2 script uses the Stage-1 cluster memberships recorded from the reported runs, in exactly the order used there (`RECORDED_KMEANS_CLUSTERS`). Stages 2 and 3 therefore start from the same clusters as the article.
- **With coordinates:** to re-execute the K-Means step itself, create `data/port_coordinates.csv` from the template (columns `port,lat,lon`). The script then runs K-Means and stops with an error if the memberships differ from the recorded ones.

## What is public and what is confidential

This follows the article's Data Availability Statement.

**Public in this repository:**
- the model parameters reported in the article and its online supplementary Appendix A:
  - port parameters (Table 1);
  - vessel specifications (Table 2);
  - initial inventories (Section 4.1);
  - cost parameters (Section 3 and Appendix A.4);
  - vessel gross tonnages and engine powers (Table A4);
  - the maritime sailing-distance matrix (Table A5);
- the model code;
- the summary results reported in the article.

**Confidential and not included:**
- the company's operational records underlying the case;
- the case workbook from which the parameters and the distance matrix were extracted;
- the full raw solver outputs.

Vessels are identified throughout by anonymized codes (CC1 to CC8). Vessel names are not disclosed.

**Limits on replication:**
- The incumbent arrangement and its reconstructed cost (Tables 3 and 8 of the article) are derived from the confidential company records. They cannot be reproduced from this repository.
- The Stage-1 K-Means step can be re-executed only if port coordinates are supplied (see above).
- The time-limited Stage-2 and Stage-3 solutions for K = 5 to 9 depend on solver version, hardware and thread count.

## Limitations stated in the article

Section 5.4 of the article lists seven limitations. In short:

1. The design is sequential, not a joint time-charter and voyage-charter optimization, and the Stage-2 penalty was not varied.
2. The charter hire comes from a regression fitted to vessels far larger than the candidates. The supplementary cost is a time-charter-equivalent proxy, and voyage-charter availability is assumed.
3. Demand, sailing times and charter rates are deterministic. Demand is a projection, and no safety stock is held.
4. Two-day periods lengthen round trips. The 183 periods cover 366 days without a terminal inventory condition, and a small residual shortage remains at the start of the horizon.
5. The origin is not modeled, every departure sails the full cluster sequence, and K-Means groups ports by coordinates that ignore land barriers.
6. Several solutions retain nonzero optimality gaps, so the configurations with five to nine clusters are not ranked.
7. The incumbent operation is a reconstruction, and the study covers a single network.

## Citation

Please cite the article (details to be completed after publication) and this repository:

> Danendra, Maulana Yafie, Arimbi Sujono, and Siti Dwi Lazuardi. 2026. *mirp-decomposition-framework: Code and Public Inputs for "Maritime Inventory Routing with Time-Charter Fleet Sizing and Supplementary Voyage Chartering for Bulk Cement Distribution"* (software). Version 1.0.0. [Archive and DOI to be added at release.]

## Licence

Code: MIT (see `LICENSE`). Public data and result tables: released with the article for research use; please cite the article.

## Contact

Corresponding author: Maulana Yafie Danendra, Department of Marine Transportation Engineering, Institut Teknologi Sepuluh Nopember (ITS), Surabaya, Indonesia.
