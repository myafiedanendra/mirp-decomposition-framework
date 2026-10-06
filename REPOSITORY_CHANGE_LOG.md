# Repository change log

**Release candidate:** 6 October 2026. Local only: not pushed, no GitHub Release, no DOI.

**Compared with:** the earlier public repository `github.com/myafiedanendra/mirp-decomposition-framework` (one commit, files dated 1 September 2026).

**Authority:** the latest author manuscript, *Maritime Inventory Routing with Time-Charter Fleet Sizing and Supplementary Voyage Chartering for Bulk Cement Distribution* (G7 final, PI-edited 6 October 2026), and its Supplementary Appendix A.

The release candidate is a full replacement of the earlier repository. Nothing in the earlier repository corresponded to the computations reported in the manuscript.

## 1. Removed

| Earlier file or content | Reason |
|---|---|
| `mirp_framework.py` | A reference skeleton, not the reported computation. It contains:<br>- great-circle (haversine) distances on coordinates, which the manuscript replaces with the maritime sailing-distance matrix;<br>- a Stage-2 objective with an opportunity-cost term "OC" for unused cargo space, which is not part of the manuscript model (Eq. 3);<br>- Stage-2 and Stage-3 functions that raise `NotImplementedError` ("available upon request");<br>- a default time limit of 3,600 s instead of 7,200 s. |
| `data/synthetic_instance.json` | Fictional instance for the skeleton. It also has a fuel price "per ton" and differs from the reported parameters. The reported public parameters are now distributed instead. |
| `data/DATA_LICENSE.md` | Offered access to the real data under a non-disclosure agreement. The manuscript's Data Availability Statement says the company records "cannot be shared", so this offer was withdrawn. |
| README: "MIRP … with cargo space utilisation" | Old framing. The manuscript treats cargo-space utilization only as a reported quantity. |
| README: "opportunity cost term penalising unused cargo space" | Retired formulation; there is no such term in the manuscript. |
| README: Stage 3 "eliminates residual stockouts" | Contradicts the manuscript, which reports a residual of about 1,766 t for K = 5. |
| README: "Gurobi 11+" | The reported runs used Gurobi 12.0.1. |
| README: examples with `-k 6` | K = 6 is no longer a focal configuration. The manuscript reports K = 5 as the lowest observed combined expenditure, with K = 5 to 9 not ranked. |
| README: "equations 1 to 25" in Appendix A | Obsolete numbering. The manuscript has Eqs. (1) to (12), and Appendix A has Eqs. (A1) to (A36). |
| README: placeholder citation and BibTeX | Replaced with the current title and authors. The DOI is to be added at release. |
| GitHub repository description: "… cargo space utilization …" | **Not editable from here.** The PI must change it on GitHub (see the release checklist). |

## 2. Replaced

| File | Now |
|---|---|
| `README.md` | Rewritten to match the manuscript:<br>- title and terminology (time-charter fleet sizing, supplementary voyage chartering);<br>- the sequential three-stage design, with the maritime sailing distances;<br>- the "lowest observed, not ranked, not a proven optimum" wording for K = 5;<br>- the residual shortage after Stage 3;<br>- the public and confidential split following the Data Availability Statement;<br>- the limits on replication. |
| `requirements.txt` | `gurobipy==12.0.1`, openpyxl, matplotlib, optional psutil. OR-Tools is listed as an optional fallback that was not used for the reported results. |
| `.gitignore` | Earlier entries kept. Adds the raw run outputs, the optional coordinate file, figure outputs, and all workbooks (`*.xlsx`), so case workbooks cannot be committed by mistake. |

## 3. Retained

| File | Note |
|---|---|
| `LICENSE` | MIT licence text unchanged ("Copyright (c) 2026 Maulana Yafie Danendra"). |
| Repository name `mirp-decomposition-framework` | Kept for now. Renaming is a PI decision (see the release checklist). |

## 4. Newly added

| File | Content and source |
|---|---|
| `mirp_option_c_seadist.py` | Stages 1 and 2 as used for the reported runs (see Section 5 for edits). |
| `supplementary_charter_milp_seadist_sweep.py` | Stage 3 as used for the reported runs (see Section 5). |
| `run_seadist_ksweep.py` | Runs Stages 1 and 2 for K = 2 to 9. Keeps the checksum check and the refuse-to-overwrite rule. Internal project-file checks removed. |
| `data/sea_distance_matrix_nm.csv` | Maritime sailing distances, Table A5. Byte-identical to the file used for the reported runs (SHA-256 `fdc43390…4dfe`). |
| `data/sea_distance_matrix_nm.meta.json` | Checksums, port codes, unit, triangle-inequality log and value policy. The confidential workbook's file names, sheet name and cell range were removed. |
| `data/ports.csv` | Sources:<br>- Table 1;<br>- origin silo capacity and loading rate (Table 1 note);<br>- initial inventories (Section 4.1);<br>- holding-cost rates (Appendix A.4). |
| `data/vessels.csv` | CC1 to CC8 specifications from Table 2, and GT and engine power from Table A4. Engine power is at the precision used in the model; Table A4 shows the same values rounded to 0.1 HP. |
| `data/parameters.csv` | Scalar cost, time and solver parameters, each with its manuscript reference. |
| `data/port_coordinates.template.csv` | Empty template. Coordinates are not distributed (see Section 6). |
| `results/stage1_clusters_by_k.csv` | Stage-1 clusters, visit sequences and sea round-trip distances, K = 2 to 9. |
| `results/stage2_summary_by_k.csv` | Stage-2 results by K (Table 5), with cost components, solver status, gap and runtime. |
| `results/stage3_combined_summary_by_k.csv` | Combined results by K (Table 6). |
| `results/stage3_vc_schedule_k5.csv` | The 34 supplementary voyages for K = 5 (Table 7), identified by vessel code only. |
| `results/figure4_k5_inventory_profiles.csv` | Data behind Figure 4. |
| `figures/make_figure2.py`, `figures/make_figure4.py` | Redraw Figures 2 and 4. The redrawn images are pixel-identical to the manuscript figure files. |
| `docs/reproducibility_notes.md` | Environment, solver behavior, hand-over rounding, figures, what cannot be reproduced, release checks. |
| `REPOSITORY_CHANGE_LOG.md`, `REPOSITORY_RELEASE_CHECKLIST.md` | This file and the pre-release checklist. |

## 5. Edits to the computational scripts (no change to model logic, inputs or results)

The scripts were taken from the reported sea-distance runs. Each edit is listed below. Equivalence with the code used for the reported runs was tested; see `docs/reproducibility_notes.md`, Section 8.

**Both model scripts:**
1. Module docstrings rewritten to the manuscript's terminology and equation numbers. Run banners, console messages, report header text and comments reworded the same way: equation references now use the manuscript and Appendix A numbering, spelling is American English, and em dashes are removed. The report lines that Stage 3 parses are unchanged.
2. Vessel display names replaced by the anonymized codes CC1 to CC8. Names are used only as output labels and, in Stage 3, to map the "Unassigned vessels" line of the Stage-2 report back to vessels. Both scripts use the same codes, so this mapping is unchanged.
3. Port latitude and longitude removed from the port dictionaries (see Section 6).
4. The unused diagnostic great-circle function `haversine_nm` removed, together with the run-manifest field that recorded great-circle distances for comparison. No model quantity used it.
5. Run-manifest fields naming the confidential workbook (file, sheet, cell range) removed. Internal review tags in comments, messages and manifest fields removed. The sea-distance checksum checks are unchanged.
6. Corrected comments:
   - Stage 2: the fuel prices are Rp per liter, as computed, not "Rp/ton";
   - Stage 2: the objective comment no longer mentions a retired utilization penalty;
   - Stage 3: the penalty comment now says the penalty does not guarantee zero shortage.

**Stage-2 script only:**
7. Optional loader for `data/port_coordinates.csv`. Without it, the recorded Stage-1 memberships are used.
8. The default `K_CLUSTERS`, used only when the environment variable is not set, changed from 6 to 5. Every reported run set K explicitly.
9. A dead line computing an unused utilization rate (`oc_rate`) was kept, with a neutral comment, so that the model code stays identical.

**Not changed:**
- the model-building and solving functions;
- all parameters;
- the distance matrix;
- solver settings;
- the recorded Stage-1 memberships;
- output formats.

## 6. Disclosure decisions applied (from the Data Availability Statement; not reopened)

**Published:**
- the model parameters reported in the article and Appendix A:
  - Table 1;
  - Table 2;
  - Section 4.1 initial inventories;
  - Section 3 and A.4 cost parameters;
  - Table A4;
  - Table A5;
- code;
- the summary results reported in the article.

**Not published:**
- company operational records;
- the case workbook;
- raw run outputs (their schedules and workbooks carry vessel names).

**Vessels:** identified only as CC1 to CC8.

**Port coordinates:** not in the article or Appendix A, so not published. Whether to publish them is left to the PI.
