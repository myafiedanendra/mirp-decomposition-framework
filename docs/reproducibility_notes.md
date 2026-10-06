# Reproducibility notes

These notes explain three things:

- how the files in this repository relate to the computations reported in the article;
- what a re-run can and cannot be expected to reproduce;
- which checks were made before release.

## 1. Reference environment of the reported runs

The run manifests of the reported runs recorded the following:

| Item | Value |
|---|---|
| Operating system | Windows 11 (build 10.0.26200) |
| Processor | AMD Ryzen 3 5300U (AMD64 Family 23 Model 104), 8 logical CPUs |
| Memory | 16 GB installed (13.8 GB visible to the operating system) |
| Python | 3.12.7 (Anaconda distribution) |
| Solver | Gurobi Optimizer 12.0.1, `Threads = 0` (all logical CPUs) |
| Stage 2 limits | `TimeLimit = 7200` s per configuration, `MIPGap = 0.02` |
| Stage 3 limits | `TimeLimit = 1200` s per configuration, `MIPGap = 0.02` |
| Stage 1 | K-Means with k-means++ initialization, 20 restarts, at most 100 iterations, seed 42 |

The Stage-2 OR-Tools fallback in `mirp_option_c_seadist.py` was not used for any reported result.

## 2. What is deterministic and what is not

**Deterministic:**
- Stage 1 (seeded K-Means and exhaustive sequencing);
- all derived voyage parameters:
  - round-trip times, period offsets and voyage costs;
  - time-charter hire;
  - fuel and port charges;
  - supplementary-voyage costs.

**Not necessarily identical on another machine:**
- **Status labels.** The solver status "OPTIMAL" in the result tables is Gurobi's status for reaching the 2% relative gap tolerance. It is not proof of optimality at zero gap.
- **K = 2 to 4.** These Stage-2 runs reached the 2% tolerance (Table 5).
- **K = 5 to 9.** These Stage-2 runs stopped at the 7,200 s limit, with gaps between 3.16% and 8.05%. The Stage-3 runs for K = 2 to 5 and K = 9 stopped at the 1,200 s limit.
- **Why outcomes can differ.** For time-limited runs, the incumbent found within the limit depends on the solver version, the number of threads and the hardware speed. A re-run can therefore return a different incumbent, with a different cost, for K = 5 to 9, even with identical inputs.
- **What stays robust.** The article's conclusions do not rest on the exact incumbents:
  - the two-vessel committed fleet for K = 5 to 9;
  - the large reduction of unmet demand by supplementary chartering;
  - the fact that the configurations with five to nine clusters are **not ranked**.

  K = 5 is reported as the configuration with the lowest observed combined expenditure, not as a proven optimum.

To compare a re-run with the article, use the files in `results/`, which hold the values reported in Tables 5 to 7.

## 3. Stage-1 clusters and port coordinates

Stage 1 clusters the destination ports on latitude and longitude (Appendix A, Eq. A1). Port coordinates are not among the model parameters reported in the article and its Data Availability Statement, so they are not distributed.

The Stage-2 script embeds the cluster memberships of the reported runs, in their recorded order, as `RECORDED_KMEANS_CLUSTERS` (K = 2 to 9). These are also listed, with visit sequences and sea round-trip distances, in `results/stage1_clusters_by_k.csv`.

- **Coordinates absent (default).** The script uses these memberships directly, so Stages 2 and 3 start from exactly the clusters of the reported runs. The run manifest records `coordinates_supplied: false`.
- **Coordinates supplied** (`data/port_coordinates.csv`, created from the template). The script runs K-Means and stops if the result differs from the recorded memberships.

For the reported runs, the K-Means memberships and their order matched the recorded memberships for every K. The order matters because it fixes the cluster indices used by Stage 2.

The visit sequence within each cluster (Eq. A2) is always recomputed from the public maritime sailing-distance matrix.

## 4. Sailing distances

**Source.** All sailing times and voyage costs in Stages 1 to 3 use `data/sea_distance_matrix_nm.csv`. This is Table A5 of the supplementary appendix, in nautical miles, used exactly as recorded: no shortest-path closure, averaging or imputation.

**Checks the scripts make before any computation:**
- the SHA-256 checksum of the CSV;
- that the metadata file refers to the same CSV;
- that the metadata records the checksum of the source workbook;
- that the unit is nautical miles.

If any check fails, the script stops without computing anything.

**Triangle inequality.** Five port pairs in the recorded matrix are longer than a two-leg path through another port (by 0.33% to 10.07%). These are listed in the metadata file and are not corrected, consistent with the "used without adjustment" note to Table A5.

## 5. Stage-2 to Stage-3 hand-over and small rounding differences

Stage 3 reads three items from each Stage-2 result folder:
- the committed fleet (from the report);
- the period-by-period inventories, from the inventory CSV, which is written with one decimal;
- the unmet demand, from the same inventory CSV.

Two consequences:

- **Unmet demand.** The Stage-2 unmet demand used by Stage 3 differs from the solver value by up to about 14 t per configuration. `results/stage3_combined_summary_by_k.csv` reports both:
  - `stage2_unmet_demand_t` is the solver value, used in the article's Table 6;
  - `stage2_unmet_demand_t_as_read_by_stage3` is the value Stage 3 reads.
- **Overflow.** The overflow of up to 0.6 t in Stage 3 (0.3 t for K = 5) comes from the same rounding, as stated in Section 4.4 of the article.

Stage 2 computes per-period demand on a 365-day year (d_p = 2 D_p / 365) over 183 two-day periods (366 modeled days), as described in Section 3.2.

## 6. Figures

- **`figures/make_figure2.py`** redraws Figure 2 from `results/stage3_combined_summary_by_k.csv`.
- **`figures/make_figure4.py`** redraws Figure 4 from `results/figure4_k5_inventory_profiles.csv`.
  - With `--recompute`, it rebuilds the post-Stage-3 trajectory from your own Stage-2 and Stage-3 outputs, by a deterministic replay of the inventory balance (Eqs. A18 and A24). This replay is not a re-optimization.
  - The replay places the residual shortage at Palu in period 0 (1,552.5 t), and at Oba in period 1 (161.9 t) and period 182 (51.1 t), 1,765.5 t in total.
  - The Stage-3 solver reports 1,766.2 t (51.7 t at Oba in the last period). This value is authoritative and is used in the article's text and tables. The replay is used only for drawing.

Both scripts were checked against the files used for the article's figures, and the redrawn images are pixel-identical.

Figures 1 and 3 are maps prepared by the authors and are not generated by code.

## 7. What cannot be reproduced from this repository

- **Incumbent arrangement.** The reconstruction of the existing (incumbent) arrangement and its cost (Tables 3 and 8 of the article) is derived from the company's route assignments and operating information. These are commercially confidential.
- **Distance matrix and parameters.** The extraction of the distance matrix and parameters from the confidential case workbook. Only the extracted public values are distributed.
- **Exact incumbents.** The exact time-limited incumbents for K = 5 to 9 on other hardware (Section 2).

## 8. Release checks

These checks were made on the release candidate.

**Equivalence with the code used for the reported runs:**
- The public scripts were compared with the code used for the reported runs, loaded with a stub solver:
  - port and vessel data (except vessel labels), constants and the distance matrix are identical;
  - for K = 2 to 9, the Stage-1 clusters and visit sequences are identical;
  - the Stage-2 voyage parameters for all 352 vessel-cluster pairs are identical;
  - the Stage-3 voyage parameters for all 72 vessel-port pairs are identical.
- **Syntax comparison of the code.** With string literals masked, the functions that build and solve the Stage-2 and Stage-3 models are identical to the code of the reported runs. They differ only in docstrings, comments and printed or report text. Edits are confined to:
  - documentation, comments, console messages and report header text;
  - vessel labels (anonymized codes);
  - removal of an unused diagnostic distance function;
  - the run-manifest fields;
  - the optional coordinate loader.

**Disclosure and figures:**
- Disclosure checks:
  - no vessel names in any file;
  - no coordinates;
  - no file names, sheet names or cell ranges of the confidential workbook;
  - no company records.
- Figures 2 and 4 redrawn from `results/` are pixel-identical to the article's figure files.

Because documentation and labels changed, a run of the public scripts records a different `script_sha256` in its manifest from the reported runs. The model and its inputs are unchanged, as shown by the checks above.
