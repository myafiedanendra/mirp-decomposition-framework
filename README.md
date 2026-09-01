# MIRP Decomposition Framework

A three-stage decomposition approach for the **Maritime Inventory Routing Problem (MIRP)** with cargo space utilisation, developed for bulk commodity distribution in archipelagic maritime networks.

This repository accompanies the paper:

> *[Author names and full citation to be inserted upon acceptance.]*

## Overview

The framework decomposes a large MIRP into three tractable stages:

- **Stage 1** — K-Means++ clustering of destination ports based on geographic coordinates, followed by a Travelling Salesman Problem (TSP) solved by complete enumeration for the intra-cluster visit sequence.
- **Stage 2** — An integrated mixed-integer linear program (MILP) that jointly determines vessel selection, cluster assignment, voyage scheduling, cargo allocation, and inventory tracking, with an explicit opportunity cost term penalising unused cargo space.
- **Stage 3** — An inventory-aware supplementary voyage charter MILP that eliminates residual stockouts by scheduling additional voyages on non-chartered vessels while respecting per-period silo capacities.

The complete mathematical formulation (equations 1 to 25) is provided in Appendix A of the paper.

## Repository contents

```
mirp-decomposition-framework/
├── README.md                      This file
├── LICENSE                        MIT licence
├── requirements.txt               Python dependencies
├── mirp_framework.py              Reference implementation (Stage 1 fully working;
                                   Stage 2 and Stage 3 skeletons)
└── data/
    ├── synthetic_instance.json    Fictional MIRP instance for demonstration
    └── DATA_LICENSE.md            Data licence and confidentiality notice
```

## Requirements

- Python 3.9 or newer
- No external libraries required for Stage 1
- Stage 2 and Stage 3 require one of:
  - **Gurobi 11+** (`pip install gurobipy`, academic licence available free from gurobi.com)
  - **Google OR-Tools** (`pip install ortools`)

## Quick start

Clone the repository and run Stage 1 on the synthetic instance:

```bash
git clone https://github.com/myafiedanendra/mirp-decomposition-framework.git
cd mirp-decomposition-framework
python mirp_framework.py --instance data/synthetic_instance.json -k 6
```

Expected output (Stage 1 completes in under one second):

```
Loading instance from: data/synthetic_instance.json
Instance summary: 9 destination ports, 8 candidate vessels, 365-day horizon.

[Stage 1a] K-Means clustering (k = 6)...
  Cluster C1: [...]
  ...

[Stage 1b] TSP per cluster...
  Cluster C1 route: origin -> ... -> origin
  ...
```

To attempt Stages 2 and 3 (requires a MILP solver):

```bash
python mirp_framework.py --stage all -k 6
```

## Instance format

An instance is a JSON file with three top-level sections. See `data/synthetic_instance.json` for a complete example.

- `meta` — planning horizon, discretisation period, exchange rate, unit costs
- `origin` — the loading terminal (name, latitude, longitude, loading rate in tonnes per hour)
- `destinations` — array of consumption ports, each with name, latitude, longitude, annual demand, silo capacity, berth depth, unloading rate, initial stock, and holding cost
- `vessels` — array of candidate vessels, each with identifier, payload capacity, gross tonnage, deadweight, engine horsepower, draft, and laden/ballast speeds

To run the framework on your own instance, prepare a JSON file with the same schema and pass it via `--instance`.

## Data availability and confidentiality

The synthetic instance in `data/synthetic_instance.json` uses **fictional numbers** and is released under the MIT licence. It is provided solely to allow readers to run and inspect the code.

The real industrial data used in the computational experiments reported in the paper is **confidential** and is not distributed with this repository. See [`data/DATA_LICENSE.md`](data/DATA_LICENSE.md) for details on how bona fide researchers may request access under a non-disclosure agreement.

## Citation

If you use this code or framework in your research, please cite:

```bibtex
@article{[key],
  title   = {[Paper title]},
  author  = {[Authors]},
  journal = {[Journal]},
  year    = {2026}
}
```

(BibTeX will be updated upon paper acceptance.)

## Licence

Source code: MIT Licence (see `LICENSE`).
Synthetic instance: MIT Licence (see `data/DATA_LICENSE.md`).
Real industrial data: not licensed for public distribution.

## Contact

For questions about the framework, real data access requests, or reproduction assistance, please contact the corresponding author (email as listed on the paper).
