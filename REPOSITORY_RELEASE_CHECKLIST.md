# Repository release checklist

Status of the local release candidate of 6 October 2026.

Key:
- [x] done and verified in the release candidate;
- [ ] for the PI, or to be done at release.

## A. Content matches the latest author manuscript

- [x] Title, authors and terminology match the G7-final author manuscript:
  - time-charter fleet sizing;
  - supplementary voyage chartering;
  - sequential three-stage decision-support framework;
  - direct financial expenditure.
- [x] All sailing times and costs use the maritime sailing-distance matrix (Table A5). There is no great-circle or haversine routing anywhere.
- [x] No unused-cargo-space penalty, opportunity-cost term or other retired formulation in the code or documentation.
- [x] K = 5 is described only as the lowest observed combined expenditure. K = 5 to 9 are "not ranked" and K = 5 is "not a proven optimum".
- [x] Stage 3 is described as leaving a residual shortage (about 1,766 t for K = 5), not as removing all shortage.
- [x] Result tables agree with the manuscript:
  - Table 5 (Stage 2);
  - Table 6 (combined);
  - Table 7 (34 voyages, K = 5).
- [x] Solver version (Gurobi 12.0.1), time limits (7,200 s and 1,200 s) and gap tolerance (2%) match Section 3.4.
- [x] Limitations summarized from Section 5.4.
- [x] Figures 2 and 4 redraw pixel-identically from `results/`.

## B. Disclosure (Data Availability Statement followed exactly)

- [x] No company operational records, case workbook or raw solver outputs.
- [x] Only parameters the manuscript reports are included:
  - Tables 1 and 2;
  - Section 4.1;
  - Section 3 and A.4;
  - Tables A4 and A5.
- [x] Vessels appear only as CC1 to CC8. A scan of every file for all vessel names found in the project sources returned none.
- [x] Distance metadata contains no workbook file names, sheet names, cell ranges or personal identifiers.
- [x] Port coordinates not distributed (the template only).
- [x] `.gitignore` blocks raw outputs, `data/port_coordinates.csv` and workbooks.

## C. Code integrity

- [x] Model-building and solving functions unchanged from the reported runs (syntax-tree comparison).
- [x] Equivalence test passed. These are identical:
  - inputs and constants;
  - Stage-1 clusters and sequences for K = 2 to 9;
  - 352 Stage-2 and 72 Stage-3 voyage-parameter sets.
- [x] All scripts compile under Python 3.
- [x] Sea-distance CSV checksum unchanged: `fdc433907aeb90247ff5fa44add3f569cac7767d57a3437f4d3b5f4bfbc54dfe`.
- [x] No optimization was re-run for this release.

## D. Before pushing (PI)

- [ ] Review this release candidate and the change log.
- [ ] **Decide on port coordinates:** keep them unpublished (current state), or publish them so that K-Means can be re-executed.
- [ ] **Decide on the repository name:** keep `mirp-decomposition-framework`, which keeps the existing URL, or rename it. GitHub redirects renamed repositories.
- [ ] Publish this release candidate on GitHub. The earlier repository was deleted by the PI on 6 October 2026, so either:
  - create a new public repository under the same account and name (gives the same URL), or
  - restore the deleted repository (possible within 90 days) and replace its contents.

  A local copy of the earlier contents is kept in `mirp-github-repo/`.
- [ ] Edit the GitHub "About" description, which currently mentions cargo-space utilization. Suggested text: "Code and public inputs for a sequential three-stage MIRP framework with time-charter fleet sizing and supplementary voyage chartering (Maritime Policy & Management submission)."
- [ ] Confirm the author names in `README.md` match the final title page.

## E. At release (after the PI approves)

- [ ] Tag `v1.0.0`, create the GitHub Release, and archive it (e.g., the Zenodo GitHub integration) to obtain a DOI.
- [ ] Replace "[Archive and DOI to be added at release.]" in `README.md` with the DOI. Optionally, add a `CITATION.cff`.
- [ ] Insert the repository DOI or URL in the manuscript's Data Availability Statement. This replaces "[PI INPUT REQUIRED: repository DOI or URL …]".
- [ ] Regenerate `SHA256SUMS.txt` if any file changes after this candidate.
