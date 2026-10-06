"""
Stage 3 of the three-stage MIRP framework: inventory-aware supplementary
voyage chartering (MILP), for K = 2..9.
=======================================================================
Takes the committed time-charter schedule of each Stage-2 run as fixed
(read from OptionC_k{K}_SeaDist_Results/), recovers the time-charter
deliveries TC[p,t], and selects direct supplementary voyages by the
uncommitted candidate vessels while tracking the post-Stage-3 inventory of
every port in every period (Eqs. 9-12 of the manuscript; Appendix A.3).

Supplementary voyage cost f[v,p] = fuel + port charges + daily time-charter
rate from Eq. (4) x round-trip days x theta, with theta = VC_PREMIUM = 1.00:
a modeled time-charter-equivalent proxy, not an observed voyage-charter
freight; candidate vessels are assumed to be available whenever deployed.
The Stage-3 penalty (Rp 50,000,000 per tonne) steers the solution toward
demand satisfaction but does not guarantee that no shortage remains
(Section 3.3). Solver: Gurobi (TimeLimit 1,200 s, MIPGap 2%).

Writes Stage3_SeaDist_kSweep_Charter_Schedule.xlsx and a run manifest
(neither is overwritten). Vessels are identified only by codes CC1 to CC8.
"""

import math
import csv
import os
import time as _time
from collections import defaultdict
import hashlib                  # provenance checksums
import json                     # distance metadata + run manifest
import platform                 # run manifest (hardware/platform)
import sys                      # run manifest (Python version)
import datetime as _dt          # run manifest timestamp

try:
    import gurobipy as gp
    from gurobipy import GRB
    USE_GUROBI = True
except ImportError:
    USE_GUROBI = False

try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False

# =============================================================
# PARAMETERS
# =============================================================
PERIOD_DAYS     = 2
TOTAL_DAYS      = 365
T_MAX           = 183       # periods (0..182)
KURS            = 15_857        # Rp per US dollar (KURS); enters the voyage-charter proxy cost
HARGA_IFO       = 18_600
HARGA_MDO       = 24_000
CHC_RATE        = 700
BUFFER_TIME_PCT = 0.10
VC_PREMIUM      = 1.00
STOCKOUT_PENALTY = 50_000_000  # Rp/ton, far above the Stage-2 penalty; does NOT guarantee zero shortage
                               # (a residual remains where a voyage is infeasible or costs more than the penalty)

ALL_VESSELS = [
    {'id': 'CC1', 'name': 'CC1',              'payload': 7000, 'GT': 4676, 'DWT': 7325,
     'HP_ME': 3746.754, 'HP_AE': 936.6885,  'draft': 7.23, 'vs_b': 11.0, 'vs_l': 8.4,  'prod_bm': 325},
    {'id': 'CC2', 'name': 'CC2',              'payload': 4000, 'GT': 2472, 'DWT': 4399,
     'HP_ME': 3549.627, 'HP_AE': 887.40675, 'draft': 6.9,  'vs_b': 11.3, 'vs_l': 7.9,  'prod_bm': 300},
    {'id': 'CC3', 'name': 'CC3',              'payload': 3600, 'GT': 2294, 'DWT': 3970,
     'HP_ME': 3549.627, 'HP_AE': 887.40675, 'draft': 4.8,  'vs_b': 12.9, 'vs_l': 6.7,  'prod_bm': 250},
    {'id': 'CC4', 'name': 'CC4',              'payload': 3400, 'GT': 3779, 'DWT': 3683,
     'HP_ME': 2958.246, 'HP_AE': 739.5615,  'draft': 4.4,  'vs_b': 11.8, 'vs_l': 8.0,  'prod_bm': 250},
    {'id': 'CC5', 'name': 'CC5',              'payload': 3400, 'GT': 2135, 'DWT': 3745,
     'HP_ME': 2716.866, 'HP_AE': 679.2165,  'draft': 4.6,  'vs_b': 12.2, 'vs_l': 5.9,  'prod_bm': 250},
    {'id': 'CC6', 'name': 'CC6',              'payload': 4000, 'GT': 2637, 'DWT': 4486,
     'HP_ME': 3746.754, 'HP_AE': 936.6885,  'draft': 6.89, 'vs_b': 12.5, 'vs_l': 9.0,  'prod_bm': 400},
    {'id': 'CC7', 'name': 'CC7',              'payload': 6000, 'GT': 3828, 'DWT': 6706,
     'HP_ME': 3549.627, 'HP_AE': 887.40675, 'draft': 5.8,  'vs_b': 12.5, 'vs_l': 8.2,  'prod_bm': 300},
    {'id': 'CC8', 'name': 'CC8',              'payload': 4500, 'GT': 3568, 'DWT': 5461,
     'HP_ME': 3648.861, 'HP_AE': 912.21525, 'draft': 5.7,  'vs_b': 17.9, 'vs_l': 11.6, 'prod_bm': 600},
]
VESSEL_BY_NAME = {v['name']: v for v in ALL_VESSELS}

ports = {
    'Biringkassi': {'loading_rate': 1500},
    'Bitung':          {'demand': 69822,  'capacity': 12000, 'depth': 10.5, 'unloading_rate': 300, 'holding_cost': 705.48, 'initial_stock': 1900},
    'Mamuju':          {'demand': 9021,   'capacity': 4000,  'depth': 10.0, 'unloading_rate': 300, 'holding_cost': 705.48, 'initial_stock': 400},
    'Palu':            {'demand': 338083, 'capacity': 8000,  'depth': 10.0, 'unloading_rate': 300, 'holding_cost': 705.48, 'initial_stock': 300},
    'Kendari':         {'demand': 145158, 'capacity': 12000, 'depth': 10.0, 'unloading_rate': 300, 'holding_cost': 705.48, 'initial_stock': 2000},
    'Ambon':           {'demand': 12205,  'capacity': 8000,  'depth': 9.2,  'unloading_rate': 300, 'holding_cost': 624.66, 'initial_stock': 2000},
    'Oba':             {'demand': 80930,  'capacity': 6000,  'depth': 9.0,  'unloading_rate': 300, 'holding_cost': 624.66, 'initial_stock': 725},
    'Celukan Bawang':  {'demand': 129014, 'capacity': 12000, 'depth': 9.6,  'unloading_rate': 100, 'holding_cost': 621.92, 'initial_stock': 1000},
    'Lembar':          {'demand': 61222,  'capacity': 5000,  'depth': 11.5, 'unloading_rate': 300, 'holding_cost': 616.44, 'initial_stock': 600},
    'Sorong':          {'demand': 50551,  'capacity': 12000, 'depth': 11.3, 'unloading_rate': 300, 'holding_cost': 726.03, 'initial_stock': 2200},
}
dest_ports = [p for p in ports if p != 'Biringkassi']

K_CONFIGS = {
    # Stage-2 result folders written by mirp_option_c_seadist.py.
    k: {'folder': os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               f'OptionC_k{k}_SeaDist_Results'),
        'prefix': f'OptionC_k{k}_'}
    for k in (2, 3, 4, 5, 6, 7, 8, 9)
}


# =============================================================
# UTILITY FUNCTIONS
# =============================================================

# =============================================================
# SAILING-DISTANCE AUTHORITY
# =============================================================
# The maritime sailing-distance matrix (nautical miles; Table A5 of the
# supplementary appendix), extracted from the confidential case workbook, is
# the ONLY sailing-distance authority in this script. Values are used EXACTLY
# AS RECORDED: no shortest-path closure, no averaging, no imputation.
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SEA_DISTANCE_CSV = os.path.join(_SCRIPT_DIR, 'data', 'sea_distance_matrix_nm.csv')
SEA_DISTANCE_META = os.path.join(_SCRIPT_DIR, 'data', 'sea_distance_matrix_nm.meta.json')
EXPECTED_SEA_CSV_SHA256 = 'fdc433907aeb90247ff5fa44add3f569cac7767d57a3437f4d3b5f4bfbc54dfe'
EXPECTED_SEA_SOURCE_SHA256 = '9a6a3b02cecdc3c512502960cfdc14c65de8f17d0ac96f87a45c5368a70a2b64'
SEA_CODE_TO_PORT = {
    'BRK': 'Biringkassi', 'BT': 'Bitung', 'MMJ': 'Mamuju', 'PL': 'Palu',
    'KDR': 'Kendari', 'AMB': 'Ambon', 'OB': 'Oba', 'LBR': 'Lembar',
    'SRG': 'Sorong', 'CB': 'Celukan Bawang',
}


def _sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def _load_sea_distance_matrix(model_ports):
    """Load and validate the sea-distance matrix. Fails loudly on any defect."""
    for path in (SEA_DISTANCE_CSV, SEA_DISTANCE_META):
        if not os.path.exists(path):
            raise SystemExit(f"[FATAL] sea-distance input missing: {path}")
    csv_sha = _sha256_file(SEA_DISTANCE_CSV)
    if csv_sha != EXPECTED_SEA_CSV_SHA256:
        raise SystemExit(f"[FATAL] sea-distance CSV checksum {csv_sha} != expected "
                         f"{EXPECTED_SEA_CSV_SHA256}")
    with open(SEA_DISTANCE_META, encoding='utf-8') as fh:
        meta = json.load(fh)
    if meta.get('csv_sha256') != csv_sha:
        raise SystemExit("[FATAL] sea-distance meta csv_sha256 does not match the CSV")
    if meta.get('source_sha256') != EXPECTED_SEA_SOURCE_SHA256:
        raise SystemExit("[FATAL] sea-distance meta source_sha256 is not the recorded source workbook")
    if meta.get('unit') != 'nautical_miles':
        raise SystemExit(f"[FATAL] sea-distance unit is {meta.get('unit')!r}, expected nautical_miles")
    with open(SEA_DISTANCE_CSV, newline='', encoding='utf-8') as fh:
        rows = list(csv.reader(fh))
    header, body = rows[0], rows[1:]
    codes = header[2:]
    if header[:2] != ['code', 'port'] or sorted(codes) != sorted(SEA_CODE_TO_PORT) or len(codes) != 10:
        raise SystemExit(f"[FATAL] unexpected sea-distance CSV header: {header}")
    if [r[0] for r in body] != codes:
        raise SystemExit("[FATAL] sea-distance CSV row codes do not match column codes")
    names = [SEA_CODE_TO_PORT[c] for c in codes]
    for r, name in zip(body, names):
        if r[1] != name:
            raise SystemExit(f"[FATAL] sea-distance CSV port name {r[1]!r} != expected {name!r}")
    if set(names) != set(model_ports) or len(set(names)) != 10:
        raise SystemExit(f"[FATAL] sea-distance ports {sorted(names)} != model ports {sorted(model_ports)}")
    mat = {}
    for r, a in zip(body, names):
        for val, b in zip(r[2:], names):
            v = float(val)
            if not math.isfinite(v):
                raise SystemExit(f"[FATAL] non-finite sea distance {a}-{b}")
            mat[(a, b)] = v
    n_pairs = 0
    for i, a in enumerate(names):
        if mat[(a, a)] != 0.0:
            raise SystemExit(f"[FATAL] non-zero diagonal for {a}")
        for b in names[i + 1:]:
            if not (mat[(a, b)] > 0):
                raise SystemExit(f"[FATAL] non-positive sea distance {a}-{b}")
            if mat[(a, b)] != mat[(b, a)]:
                raise SystemExit(f"[FATAL] asymmetric sea distance {a}-{b}")
            n_pairs += 1
    if n_pairs != 45:
        raise SystemExit(f"[FATAL] expected 45 unordered port pairs, found {n_pairs}")
    return mat, meta, csv_sha


# Validated at import time, i.e. before any model can be built.
SEA_NM, SEA_META, SEA_CSV_SHA256 = _load_sea_distance_matrix(set(ports.keys()))
_SEA_PORTS = frozenset(ports.keys())


def sea_nm(origin_name, destination_name):
    """Authoritative sailing distance in nautical miles (maritime matrix)."""
    if origin_name not in _SEA_PORTS:
        raise KeyError(f"sea_nm: unknown port {origin_name!r}")
    if destination_name not in _SEA_PORTS:
        raise KeyError(f"sea_nm: unknown port {destination_name!r}")
    if origin_name == destination_name:
        return 0.0
    return SEA_NM[(origin_name, destination_name)]


def _environment_record():
    """Software/hardware record for run manifests."""
    rec = {
        'python_version': sys.version,
        'platform': platform.platform(),
        'processor': platform.processor() or platform.machine(),
        'logical_cpus': os.cpu_count(),
    }
    try:
        import psutil  # optional
        rec['ram_gb'] = round(psutil.virtual_memory().total / 1024 ** 3, 1)
    except Exception:
        rec['ram_gb'] = 'unavailable (psutil not installed)'
    try:
        rec['gurobi_version'] = '.'.join(str(x) for x in gp.gurobi.version()) if USE_GUROBI else None
    except Exception as exc:
        rec['gurobi_version'] = f'unavailable ({exc})'
    return rec


def _write_manifest(path, payload):
    """Write a JSON manifest; refuses to overwrite."""
    if os.path.exists(path):
        raise SystemExit(f"[FATAL] manifest already exists, refusing to overwrite: {path}")
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False, default=str)


def compute_biaya_tunda(GT):
    if GT <= 2000:    return 367_500
    elif GT <= 3500:  return 486_500
    elif GT <= 8000:  return 755_000
    elif GT <= 14000: return 1_171_000
    else:             return 1_500_000


def compute_voyage_params(vessel, port_name):
    """Compute voyage parameters for vessel: Biringkassi -> port -> Biringkassi at FULL payload."""
    origin = ports['Biringkassi']
    dest = ports[port_name]
    cargo_tons = vessel['payload']
    dist_nm = sea_nm('Biringkassi', port_name)

    sail_out_days = dist_nm / (vessel['vs_l'] * 24)
    sail_back_days = dist_nm / (vessel['vs_b'] * 24)
    sea_days = sail_out_days + sail_back_days

    load_days = cargo_tons / (vessel['prod_bm'] * 24)
    unload_days = cargo_tons / (dest['unloading_rate'] * 24)
    port_days = load_days + unload_days

    buffer_days = (sea_days + port_days) * BUFFER_TIME_PCT
    rt_days = sea_days + port_days + buffer_days
    rt_periods = math.ceil(rt_days / PERIOD_DAYS)

    # One-way arrival offset (laden leg only)
    arrival_offset_days = sail_out_days
    arrival_offset_periods = math.ceil(arrival_offset_days / PERIOD_DAYS)

    # Fuel cost (full payload basis)
    HP_ME = vessel['HP_ME']; HP_AE = vessel['HP_AE']
    me_base = (HP_ME * 0.18 * 24) / 1000 * 1123.6
    me_fuel = me_base * 1.0 * sea_days + me_base * 0.2 * port_days
    ae_base = (HP_AE * 0.18 * 24) / 1000 * 1201.92
    ae_fuel = ae_base * 0.5 * sea_days + ae_base * 1.0 * port_days
    fuel_cost = me_fuel * HARGA_IFO + ae_fuel * HARGA_MDO

    # Port charges
    GT = vessel['GT']; n_calls = 2
    labuh = GT * 83 * n_calls
    pandu = (99_500 + GT * 28) * n_calls
    tunda = compute_biaya_tunda(GT) * n_calls
    tambat_origin = GT * 80 * math.ceil(load_days)
    tambat_dest = GT * 80 * math.ceil(unload_days)
    port_charges = labuh + pandu + tunda + tambat_origin + tambat_dest

    # Hire cost
    daily_usd = vessel['DWT'] * 0.0401 + 18_318
    hire_cost = daily_usd * KURS * VC_PREMIUM * rt_days

    # Fixed voyage cost (everything except CHC; CHC is a per-ton variable)
    fixed_cost = fuel_cost + port_charges + hire_cost

    return {
        'dist_nm': dist_nm,
        'rt_days': rt_days,
        'rt_periods': rt_periods,
        'arrival_offset_periods': arrival_offset_periods,
        'arrival_offset_days': arrival_offset_days,
        'fixed_cost': fixed_cost,
        'fuel_cost': fuel_cost,
        'port_charges': port_charges,
        'hire_cost': hire_cost,
    }


# =============================================================
# READ STAGE 2 DATA
# =============================================================

def read_unassigned_vessels(folder, prefix):
    report_file = os.path.join(folder, f"{prefix}Report.txt")
    with open(report_file, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            if 'Unassigned vessels:' in line:
                names_str = line.split(':', 1)[1].strip()
                names = [n.strip() for n in names_str.split(',') if n.strip()]
                return [VESSEL_BY_NAME[n] for n in names if n in VESSEL_BY_NAME]
    return list(ALL_VESSELS)


def read_stage2_inventory(folder, prefix):
    """Read Stage 2 inventory and stockout data. Returns (inv_dict, so_dict)."""
    inv_file = os.path.join(folder, f"{prefix}Inventory.csv")
    with open(inv_file) as f:
        sample = f.read(2048)
        delimiter = ';' if sample.count(';') > sample.count(',') else ','
        f.seek(0)
        rows = list(csv.DictReader(f, delimiter=delimiter))

    inv = {}; so = {}
    for p in dest_ports:
        inv[p] = []; so[p] = []
    for row in rows:
        for p in dest_ports:
            inv[p].append(float(row[f's_{p}']))
            so[p].append(float(row[f'so_{p}']))
    return inv, so


def derive_tc_deliveries(inv, so):
    """Derive TC delivery events from Stage 2 inventory transitions.
    TC_del[p,t] = s[p,t] - s[p,t-1] + demand[p] - so[p,t]
    """
    demand_per_period = {p: ports[p]['demand'] * PERIOD_DAYS / TOTAL_DAYS for p in dest_ports}
    tc_del = {}
    for p in dest_ports:
        tc_del[p] = {}
        for t in range(T_MAX):
            prev = ports[p]['initial_stock'] if t == 0 else inv[p][t-1]
            delivery = inv[p][t] - prev + demand_per_period[p] - so[p][t]
            if delivery > 0.5:
                tc_del[p][t] = delivery
    return tc_del


def read_mirp_total_cost(folder, prefix):
    report_file = os.path.join(folder, f"{prefix}Report.txt")
    total = 0; stockout_penalty = 0
    with open(report_file, 'r', encoding='utf-8', errors='replace') as f:
        lines = f.readlines()
    in_cost = False
    for line in lines:
        if 'COST BREAKDOWN' in line:
            in_cost = True; continue
        if in_cost and 'TOTAL:::' in line:
            for p in line.strip().split():
                cleaned = p.replace(',', '')
                try:
                    val = float(cleaned)
                    if val > 1e9: total = val; break
                except ValueError: continue
            in_cost = False
        if in_cost and 'Stockout' in line:
            for p in line.strip().split():
                cleaned = p.replace(',', '')
                try:
                    val = float(cleaned)
                    if val > 1000: stockout_penalty = val; break
                except ValueError: continue
    return total, stockout_penalty


# =============================================================
# STAGE 3 MILP: INVENTORY-AWARE SUPPLEMENTARY CHARTER
# =============================================================

def solve_stage3_inventory_aware(k_value, folder, prefix, available_vessels):
    """
    Inventory-aware Stage 3 MILP.

    Decision variables:
      w[v,p,t] ∈ {0,1}  : vessel v departs for port p at period t
      q[v,p,t] >= 0      : VC cargo carried
      s_prime[p,t] >= 0   : post-Stage 3 inventory
      so_prime[p,t] >= 0   : residual stockout (deficit slack)
      ov_prime[p,t] >= 0   : overflow (surplus slack: cargo exceeding capacity)

    Objective: min Σ fixed_cost*w + CHC*q + penalty*(so_prime + ov_prime)

    Constraints:
      (19) q[v,p,t] <= payload * w[v,p,t]
      (20) Σ_active w[v,p,tau] <= 1  (non-overlap)
      (21) s'[p,t] = s'[p,t-1] + TC[p,t] + Σ q_vc[v,p,t-α] - dp + so'[p,t] - ov'[p,t]
      (22) s'[p,t] <= capacity (enforced via variable bound)
      (23) w[v,p,t] = 0  if t + RTD > Tmax
    """
    if not USE_GUROBI:
        print("    [ERROR] Gurobi required for inventory-aware Stage 3")
        return None

    t0 = _time.time()

    # Read Stage 2 data
    inv_s2, so_s2 = read_stage2_inventory(folder, prefix)
    tc_del = derive_tc_deliveries(inv_s2, so_s2)
    demand_per_period = {p: ports[p]['demand'] * PERIOD_DAYS / TOTAL_DAYS for p in dest_ports}

    # Check if there's any stockout to cover
    total_stockout = sum(sum(so_s2[p]) for p in dest_ports)
    if total_stockout < 0.5:
        print("  No stockout: no supplementary charter needed.")
        return {
            'total_cost': 0, 'voyages': [], 'vessels_used': set(),
            'n_vessels_used': 0, 'n_voyages': 0, 'total_distance_nm': 0,
            'runtime': 0, 'gap': 0, 'status': 'OPTIMAL (trivial)',
            'obj_val': 0.0, 'obj_bound': 0.0, 'sol_count': 0,
            'post_s3_inv': {p: [inv_s2[p][t] for t in range(T_MAX)] for p in dest_ports},
            'post_s3_so': {p: [0.0]*T_MAX for p in dest_ports},
            'total_remaining_stockout': 0,
        }

    # Identify ports with nonzero stockout
    ports_with_so = [p for p in dest_ports if sum(so_s2[p]) > 0.5]
    print(f"    Ports with stockout: {len(ports_with_so)}: {', '.join(ports_with_so)}")
    print(f"    Total Stage 2 stockout: {total_stockout:,.0f} tons")

    # Pre-compute voyage parameters for each (vessel, port)
    n_v = len(available_vessels)
    voy_params = {}  # (vi, port) -> params
    for vi, vessel in enumerate(available_vessels):
        for p in dest_ports:
            if vessel['draft'] > ports[p]['depth']:
                continue  # draft infeasible
            voy_params[(vi, p)] = compute_voyage_params(vessel, p)

    # Build MILP
    model = gp.Model(f"Stage3_InvAware_k{k_value}")
    model.Params.OutputFlag = 0
    model.Params.TimeLimit = 1200  # 20 min per k
    model.Params.MIPGap = 0.02   # 2% gap tolerance

    # === Decision variables ===

    # w[v,p,t]: binary departure variable
    w = {}
    for vi in range(n_v):
        for p in dest_ports:
            if (vi, p) not in voy_params:
                continue
            rtd = voy_params[(vi, p)]['rt_periods']
            for t in range(T_MAX):
                if t + rtd > T_MAX:
                    break  # Eq. (A26): horizon feasibility
                w[vi, p, t] = model.addVar(vtype=GRB.BINARY, name=f"w_{vi}_{p}_{t}")

    # q[v,p,t]: VC cargo
    q = {}
    for (vi, p, t) in w:
        q[vi, p, t] = model.addVar(lb=0, name=f"q_{vi}_{p}_{t}")

    # s_prime[p,t]: post-Stage 3 inventory
    s_prime = {}
    for p in dest_ports:
        for t in range(T_MAX):
            s_prime[p, t] = model.addVar(lb=0, ub=ports[p]['capacity'],
                                          name=f"sp_{p}_{t}")

    # so_prime[p,t]: residual stockout: deficit slack (inventory would go below 0)
    so_prime = {}
    for p in dest_ports:
        for t in range(T_MAX):
            so_prime[p, t] = model.addVar(lb=0, name=f"sop_{p}_{t}")

    # ov_prime[p,t]: overflow: surplus slack (inventory would exceed capacity)
    ov_prime = {}
    for p in dest_ports:
        for t in range(T_MAX):
            ov_prime[p, t] = model.addVar(lb=0, name=f"ovp_{p}_{t}")

    model.update()

    n_w = len(w); n_q = len(q); n_sp = len(s_prime); n_sop = len(so_prime); n_ov = len(ov_prime)
    print(f"    Variables: w={n_w} (binary), q={n_q}, s'={n_sp}, so'={n_sop}, ov'={n_ov}")
    print(f"    Total: {n_w + n_q + n_sp + n_sop + n_ov}")

    # === Constraints ===

    # Eq. (A22): cargo capacity
    for (vi, p, t) in w:
        vessel = available_vessels[vi]
        model.addConstr(q[vi, p, t] <= vessel['payload'] * w[vi, p, t],
                        name=f"cap_{vi}_{p}_{t}")

    # Eq. (A23): non-overlap; at any period tau, vessel v has at most 1 active voyage
    for vi in range(n_v):
        # Collect all feasible (port, t) for this vessel
        vessel_voyages = [(p, t) for (v, p, t) in w if v == vi]
        if not vessel_voyages:
            continue

        for tau in range(T_MAX):
            active_vars = []
            for p in dest_ports:
                if (vi, p) not in voy_params:
                    continue
                rtd = voy_params[(vi, p)]['rt_periods']
                for t in range(max(0, tau - rtd + 1), tau + 1):
                    if (vi, p, t) in w:
                        active_vars.append(w[vi, p, t])
            if len(active_vars) > 1:
                model.addConstr(gp.quicksum(active_vars) <= 1,
                                name=f"noovlp_{vi}_{tau}")

    # Eq. (A24): inventory balance
    for p in dest_ports:
        for t in range(T_MAX):
            # Previous inventory
            if t == 0:
                prev_inv_val = ports[p]['initial_stock']
            else:
                prev_inv_val = None  # will use variable

            # TC delivery at period t (fixed from Stage 2)
            tc_at_t = tc_del[p].get(t, 0)

            # VC delivery at period t: sum of q[v,p,t-alpha] for all vessels
            vc_delivery_vars = []
            for vi in range(n_v):
                if (vi, p) not in voy_params:
                    continue
                alpha = voy_params[(vi, p)]['arrival_offset_periods']
                dep_t = t - alpha
                if dep_t >= 0 and (vi, p, dep_t) in q:
                    vc_delivery_vars.append(q[vi, p, dep_t])

            # Build constraint: s'[p,t] = prev + TC + VC - demand + so'[p,t] - ov'[p,t]
            # so' absorbs deficit (would-be negative inventory)
            # ov' absorbs surplus (would-be overflow above capacity)
            demand = demand_per_period[p]

            if t == 0:
                rhs = prev_inv_val + tc_at_t - demand
                if vc_delivery_vars:
                    model.addConstr(
                        s_prime[p, t] == rhs + gp.quicksum(vc_delivery_vars)
                        + so_prime[p, t] - ov_prime[p, t],
                        name=f"invbal_{p}_{t}")
                else:
                    model.addConstr(
                        s_prime[p, t] == rhs + so_prime[p, t] - ov_prime[p, t],
                        name=f"invbal_{p}_{t}")
            else:
                rhs_expr = s_prime[p, t-1] + tc_at_t - demand
                if vc_delivery_vars:
                    model.addConstr(
                        s_prime[p, t] == rhs_expr + gp.quicksum(vc_delivery_vars)
                        + so_prime[p, t] - ov_prime[p, t],
                        name=f"invbal_{p}_{t}")
                else:
                    model.addConstr(
                        s_prime[p, t] == rhs_expr + so_prime[p, t] - ov_prime[p, t],
                        name=f"invbal_{p}_{t}")

    # Note: Eq. (A25) capacity is enforced via ub on s_prime variables
    # Note: Eq. (A26) horizon is enforced by not creating w variables beyond limit

    # === Objective ===
    obj = gp.LinExpr()

    # Voyage cost (fixed per voyage + CHC per ton)
    for (vi, p, t) in w:
        vp = voy_params[(vi, p)]
        obj.add(w[vi, p, t], vp['fixed_cost'])
        obj.add(q[vi, p, t], CHC_RATE)

    # Stockout penalty
    for p in dest_ports:
        for t in range(T_MAX):
            obj.add(so_prime[p, t], STOCKOUT_PENALTY)

    # Overflow penalty (same as stockout; wasted cargo is equally costly)
    for p in dest_ports:
        for t in range(T_MAX):
            obj.add(ov_prime[p, t], STOCKOUT_PENALTY)

    model.setObjective(obj, GRB.MINIMIZE)
    model.update()

    print(f"    Constraints: {model.NumConstrs}")
    print(f"    Solving (TimeLimit={model.Params.TimeLimit}s, MIPGap={model.Params.MIPGap:.0%})...")

    model.optimize()

    elapsed = _time.time() - t0

    if model.SolCount == 0:
        print("    [ERROR] No feasible solution found")
        return None

    status_str = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.TIME_LIMIT: f"TIME_LIMIT (gap={model.MIPGap:.1%})",
    }.get(model.Status, f"Status={model.Status}")

    # === Extract solution ===
    voyages = []
    vessels_used = set()
    total_cost = 0
    total_distance = 0

    for (vi, p, t) in w:
        if w[vi, p, t].X > 0.5:
            vessel = available_vessels[vi]
            vp = voy_params[(vi, p)]
            cargo = q[vi, p, t].X

            if cargo < 0.5:
                continue  # skip zero-cargo departures

            vessels_used.add(vessel['id'])
            arr_period = t + vp['arrival_offset_periods']
            voyage_cost = vp['fixed_cost'] + CHC_RATE * cargo

            voyages.append({
                'vessel_id': vessel['id'],
                'vessel_name': vessel['name'],
                'vessel_payload': vessel['payload'],
                'port': p,
                'cargo': cargo,
                'dep_period': t,
                'dep_day': t * PERIOD_DAYS,
                'arrival_period': arr_period,
                'arrival_day': round(t * PERIOD_DAYS + vp['arrival_offset_days'], 1),
                'rt_days': vp['rt_days'],
                'rt_periods': vp['rt_periods'],
                'dist_nm': vp['dist_nm'] * 2,
                'fuel_cost': vp['fuel_cost'],
                'port_charges': vp['port_charges'],
                'hire_cost': vp['hire_cost'],
                'chc': CHC_RATE * cargo,
                'total_cost': voyage_cost,
                'unit_cost': voyage_cost / cargo if cargo > 0 else 0,
                'deadline_period': 0,
                'deadline_day': 0,
            })

            total_cost += voyage_cost
            total_distance += vp['dist_nm'] * 2

    voyages.sort(key=lambda v: (v['dep_period'], v['vessel_id']))

    # Extract post-Stage 3 inventory, stockout, and overflow
    post_s3_inv = {}; post_s3_so = {}; post_s3_ov = {}
    total_remaining_so = 0; total_overflow = 0
    for p in dest_ports:
        post_s3_inv[p] = [s_prime[p, t].X for t in range(T_MAX)]
        post_s3_so[p] = [so_prime[p, t].X for t in range(T_MAX)]
        post_s3_ov[p] = [ov_prime[p, t].X for t in range(T_MAX)]
        total_remaining_so += sum(post_s3_so[p])
        total_overflow += sum(post_s3_ov[p])

    # Summary
    print(f"\n    Status: {status_str} | Obj: Rp {model.ObjVal:,.0f} | Runtime: {elapsed:.1f}s")
    print(f"    Voyages: {len(voyages)} | Vessels: {len(vessels_used)} ({', '.join(sorted(vessels_used))})")
    print(f"    Total VC cost: Rp {total_cost/1e9:,.2f} B")
    print(f"    Total remaining stockout: {total_remaining_so:,.1f} tons")
    if total_overflow > 0.5:
        print(f"    Total overflow (wasted): {total_overflow:,.1f} tons")

    # Per-port stockout summary
    if total_remaining_so > 0.5:
        print(f"    Remaining stockout by port:")
        for p in dest_ports:
            port_so = sum(post_s3_so[p])
            if port_so > 0.5:
                so_periods = sum(1 for x in post_s3_so[p] if x > 0.5)
                print(f"      {p:<18}: {port_so:>8,.1f} tons in {so_periods} periods (initial transient)")

    # Per-port overflow summary (should be near-zero if optimizer works well)
    if total_overflow > 1.0:
        print(f"    Overflow by port:")
        for p in dest_ports:
            port_ov = sum(post_s3_ov[p])
            if port_ov > 0.5:
                ov_periods = sum(1 for x in post_s3_ov[p] if x > 0.5)
                print(f"      {p:<18}: {port_ov:>8,.1f} tons in {ov_periods} periods")

    return {
        'total_cost': total_cost,
        'total_distance_nm': total_distance,
        'voyages': voyages,
        'vessels_used': vessels_used,
        'n_vessels_used': len(vessels_used),
        'n_voyages': len(voyages),
        'runtime': elapsed,
        'gap': model.MIPGap if hasattr(model, 'MIPGap') else 0,
        'status': status_str,
        # reporting-only metadata (no formulation change):
        'obj_val': model.ObjVal,
        'obj_bound': model.ObjBound,
        'sol_count': model.SolCount,
        'post_s3_inv': post_s3_inv,
        'post_s3_so': post_s3_so,
        'post_s3_ov': post_s3_ov,
        'total_remaining_stockout': total_remaining_so,
        'total_overflow': total_overflow,
    }


# =============================================================
# MAIN
# =============================================================


# =============================================================
# FINAL AUTHORITATIVE k-SWEEP ORCHESTRATION (reporting/validation only;
# Stage-3 mathematical formulation above is UNCHANGED vs the approved k6 file)
# =============================================================
K_SWEEP = [2, 3, 4, 5, 6, 7, 8, 9]
_RECON_TOL = 100.0          # Rp tolerance for financial reconciliation (rounding)
STAGE2_SO_PENALTY = 1_225_000  # Stage-2 stockout penalty rate (for CHECK 5 cross-check only)


def _read_stage2_meta(folder, prefix):
    """Read Stage-2 solver Status and MIP Gap from the report header (for reporting)."""
    status, gap = "NA", None
    path = os.path.join(folder, f"{prefix}Report.txt")
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if "Solver Status" in line:
                    status = line.split(":", 1)[1].strip()
                elif line.strip().startswith("MIP Gap"):
                    tok = line.split(":", 1)[1].strip().replace("%", "")
                    try: gap = float(tok) / 100.0
                    except ValueError: pass
    except FileNotFoundError:
        pass
    return status, gap


def _read_financial_line(folder, prefix):
    """Read the 'Financial (direct, excl. penalty)' Rp value from the Stage-2 report (CHECK 4)."""
    path = os.path.join(folder, f"{prefix}Report.txt")
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if "Financial" in line and "direct" in line:
                    for tok in line.replace(",", " ").split():
                        try:
                            v = float(tok)
                            if v > 1e9:
                                return v
                        except ValueError:
                            continue
    except FileNotFoundError:
        return None
    return None


def _write_sweep_workbook(rows, schedules, out_path):
    wb = Workbook()
    ws = wb.active; ws.title = "Summary"
    cols = ["k","Stage2_Status","Stage2_MIPGap","Stage2_Financial_Cost","Stage2_Stockout_t",
            "Stage3_Status","Stage3_ObjVal","Stage3_ObjBound","Stage3_MIPGap","Stage3_Runtime_s",
            "Stage3_SolCount","VC_Vessels_Used","VC_Vessel_IDs","VC_Voyages","VC_Cargo_t",
            "VC_Financial_Cost","Residual_Stockout_t","Overflow_t","Combined_Financial_Cost"]
    ws.append(cols)
    for c in ws[1]: c.font = Font(bold=True)
    for r in rows:
        ws.append([r.get(k) for k in cols])
    for col in "ABCDEFGHIJKLMNOPQRS":
        ws.column_dimensions[col].width = 18
    sched_cols = ["vessel_id","vessel_name","vessel_payload","port","cargo","dep_period","dep_day",
                  "arrival_period","arrival_day","rt_days","rt_periods","dist_nm","fuel_cost",
                  "port_charges","hire_cost","chc","total_cost","unit_cost"]
    for k in sorted(schedules):
        wsk = wb.create_sheet(f"Schedule k={k}")
        wsk.append(sched_cols)
        for c in wsk[1]: c.font = Font(bold=True)
        for voy in schedules[k]:
            wsk.append([voy.get(c) for c in sched_cols])
        for col in "ABCDEFGHIJKLMNOPQR":
            wsk.column_dimensions[col].width = 15
    wb.save(out_path)


def main():
    print("=" * 100)
    print("STAGE 3: supplementary voyage chartering, k-sweep (k = 2..9)")
    print("=" * 100)
    print(f"KURS = Rp {KURS:,}/USD | VC premium x{VC_PREMIUM:.2f} | Stage-3 penalty Rp {STOCKOUT_PENALTY:,}/ton")
    print(f"Stage-3 solver: TimeLimit=1200 s, MIPGap=2%")

    # CHECK 3
    if KURS != 15857:
        raise SystemExit(f"[FATAL] CHECK 3 failed: KURS={KURS} (expected 15857)")
    if not USE_GUROBI:
        raise SystemExit("[FATAL] Gurobi is required for inventory-aware Stage 3 (none available).")

    # Output isolation: refuse to overwrite an existing workbook or manifest.
    out_path = os.path.join(_SCRIPT_DIR, "Stage3_SeaDist_kSweep_Charter_Schedule.xlsx")
    manifest_path = os.path.join(_SCRIPT_DIR, "Stage3_SeaDist_run_manifest.json")
    for pth in (out_path, manifest_path):
        if os.path.exists(pth):
            raise SystemExit(f"[FATAL] output already exists, refusing to overwrite: {pth}")
    manifest_k = {}

    rows, schedules = [], {}

    for k in K_SWEEP:
        print("\n" + "#" * 100)
        print(f"#  k = {k}")
        print("#" * 100)
        cfg = K_CONFIGS.get(k)
        if cfg is None:
            raise SystemExit(f"[FATAL] k={k}: no K_CONFIGS entry")
        folder, prefix = cfg["folder"], cfg["prefix"]

        # CHECK 1 + CHECK 2 (fail-fast; no substitution)
        rpt = os.path.join(folder, f"{prefix}Report.txt")
        invcsv = os.path.join(folder, f"{prefix}Inventory.csv")
        if not os.path.isdir(folder):
            raise SystemExit(f"[FATAL] k={k}: Stage-2 Final folder missing: {folder}")
        for req in (rpt, invcsv):
            if not os.path.exists(req):
                raise SystemExit(f"[FATAL] k={k}: required Stage-2 file missing: {req}")
        s2_manifest_path = os.path.join(folder, f"run_manifest_k{k}.json")
        if not os.path.exists(s2_manifest_path):
            raise SystemExit(f"[FATAL] k={k}: Stage-2 SeaDist run manifest missing: {s2_manifest_path}")
        with open(s2_manifest_path, encoding='utf-8') as fh:
            s2_manifest = json.load(fh)
        if s2_manifest.get('distance_csv_sha256') != SEA_CSV_SHA256:
            raise SystemExit(f"[FATAL] k={k}: Stage-2 run used a different distance CSV "
                             f"({s2_manifest.get('distance_csv_sha256')})")

        # Provenance
        print(f"  INPUT FOLDER : {folder}")
        print(f"  PREFIX       : {prefix}")
        print(f"  KURS         : Rp {KURS:,}/USD")

        # Stage-2 reads
        charter_pool = read_unassigned_vessels(folder, prefix)
        mirp_total, stockout_penalty = read_mirp_total_cost(folder, prefix)
        base_cost = mirp_total - stockout_penalty            # financial Stage-2
        inv_s2, so_s2 = read_stage2_inventory(folder, prefix)
        total_stockout_s2 = sum(sum(so_s2[p]) for p in dest_ports)
        s2_status, s2_gap = _read_stage2_meta(folder, prefix)

        print(f"  Stage-2 MIRP objective      : Rp {mirp_total:,.0f}")
        print(f"  Stage-2 stockout penalty    : Rp {stockout_penalty:,.0f}")
        print(f"  Stage-2 financial/base cost : Rp {base_cost:,.0f}")
        print(f"  Stage-2 stockout quantity   : {total_stockout_s2:,.1f} ton")
        print(f"  Candidate VC pool           : {', '.join(v['id'] for v in charter_pool)}")

        # CHECK 4: report 'Financial' line vs (mirp_total - stockout)
        fin_line = _read_financial_line(folder, prefix)
        if fin_line is not None and abs(fin_line - base_cost) > max(_RECON_TOL, 1e-6 * base_cost):
            raise SystemExit(f"[FATAL] k={k} CHECK 4 failed: report Financial {fin_line:,.0f} != "
                             f"mirp_total-stockout {base_cost:,.0f}")

        # CHECK 5: stockout consistency (penalty_rp / Stage-2 rate == sum of so_s2)
        implied = stockout_penalty / STAGE2_SO_PENALTY
        if abs(implied - total_stockout_s2) > 1.0:
            print(f"  [WARN] CHECK 5: Stage-2 stockout {total_stockout_s2:,.1f} t vs penalty-implied "
                  f"{implied:,.1f} t (delta {implied - total_stockout_s2:+.1f})")

        # Solve (or trivial if no stockout)
        if total_stockout_s2 <= 0.5:
            sol = {"total_cost": 0.0, "voyages": [], "vessels_used": set(), "n_vessels_used": 0,
                   "n_voyages": 0, "runtime": 0.0, "gap": 0.0,
                   "status": "OPTIMAL (no supplementary VC needed)",
                   "post_s3_so": {}, "post_s3_ov": {}, "total_remaining_stockout": 0.0,
                   "total_overflow": 0.0, "obj_val": 0.0, "obj_bound": 0.0, "sol_count": 0}
        else:
            sol = solve_stage3_inventory_aware(k, folder, prefix, charter_pool)
        if sol is None:
            raise SystemExit(f"[FATAL] k={k}: Stage-3 solve returned NO feasible solution. "
                             f"Stopping the sweep (no substitution, no parameter change).")

        # CHECK 6: VC vessels subset of Stage-2 unassigned pool
        pool_ids = {v["id"] for v in charter_pool}
        if not set(sol["vessels_used"]).issubset(pool_ids):
            raise SystemExit(f"[FATAL] k={k} CHECK 6 failed: VC vessels {sol['vessels_used']} "
                             f"not subset of Stage-2 unassigned pool {pool_ids}")

        # CHECK 7: cargo per voyage <= payload
        for voy in sol["voyages"]:
            if voy["cargo"] > voy["vessel_payload"] + 1e-6:
                raise SystemExit(f"[FATAL] k={k} CHECK 7 failed: cargo {voy['cargo']:.1f} > payload "
                                 f"{voy['vessel_payload']} ({voy['vessel_id']} -> {voy['port']})")

        vc_financial = sol["total_cost"]
        combined = base_cost + vc_financial                  # CHECK 8

        # CHECK 8 detail: Stage-3 objective = VC financial + penalty*(residual + overflow)
        recon_obj = vc_financial + STOCKOUT_PENALTY * (sol["total_remaining_stockout"] + sol["total_overflow"])
        if sol.get("obj_val", 0) and abs(recon_obj - sol["obj_val"]) > max(_RECON_TOL, 1e-4 * abs(sol["obj_val"])):
            print(f"  [WARN] Stage-3 objective reconciliation: recon {recon_obj:,.0f} vs ObjVal "
                  f"{sol['obj_val']:,.0f} (delta {recon_obj - sol['obj_val']:+,.0f})")

        # CHECK 10: overflow
        if sol["total_overflow"] > 1.0:
            print(f"  WARNING: NONZERO STAGE-3 OVERFLOW = {sol['total_overflow']:,.1f} ton")

        # Residual stockout by port / timing
        resid_by_port = {}
        for p in dest_ports:
            arr = sol.get("post_s3_so", {}).get(p, [])
            tot = sum(arr)
            if tot > 0.5:
                periods = [t for t, x in enumerate(arr) if x > 0.5]
                resid_by_port[p] = (tot, periods)
        total_vc_cargo = sum(v["cargo"] for v in sol["voyages"])

        print(f"  Stage-3: status={sol['status']} | ObjVal=Rp {sol.get('obj_val',0):,.0f} | "
              f"ObjBound=Rp {sol.get('obj_bound',0):,.0f} | gap={sol['gap']:.4f} | "
              f"runtime={sol['runtime']:.1f}s | solcount={sol.get('sol_count',0)}")
        print(f"  VC: voyages={sol['n_voyages']} | vessels={sorted(sol['vessels_used'])} | "
              f"cargo={total_vc_cargo:,.1f} t | VC financial=Rp {vc_financial:,.0f}")
        print(f"  Residual stockout={sol['total_remaining_stockout']:,.1f} t | "
              f"overflow={sol['total_overflow']:,.1f} t | COMBINED financial=Rp {combined:,.0f}")
        if resid_by_port:
            for p, (tot, per) in resid_by_port.items():
                print(f"      residual {p}: {tot:,.1f} t in periods {per[:8]}{'...' if len(per) > 8 else ''}")

        rows.append({
            "k": k, "Stage2_Status": s2_status,
            "Stage2_MIPGap": (round(s2_gap, 4) if s2_gap is not None else "NA"),
            "Stage2_Financial_Cost": round(base_cost, 0), "Stage2_Stockout_t": round(total_stockout_s2, 1),
            "Stage3_Status": sol["status"], "Stage3_ObjVal": round(sol.get("obj_val", 0), 0),
            "Stage3_ObjBound": round(sol.get("obj_bound", 0), 0), "Stage3_MIPGap": round(sol["gap"], 4),
            "Stage3_Runtime_s": round(sol["runtime"], 1), "Stage3_SolCount": sol.get("sol_count", 0),
            "VC_Vessels_Used": sol["n_vessels_used"], "VC_Vessel_IDs": ", ".join(sorted(sol["vessels_used"])),
            "VC_Voyages": sol["n_voyages"], "VC_Cargo_t": round(total_vc_cargo, 1),
            "VC_Financial_Cost": round(vc_financial, 0),
            "Residual_Stockout_t": round(sol["total_remaining_stockout"], 1),
            "Overflow_t": round(sol["total_overflow"], 1),
            "Combined_Financial_Cost": round(combined, 0),
        })
        schedules[k] = sol["voyages"]

        voyage_params = []
        for vessel in charter_pool:
            for p in dest_ports:
                vp = compute_voyage_params(vessel, p)
                voyage_params.append({
                    'vessel': vessel['id'], 'port': p,
                    'dist_nm_sea_one_way': vp['dist_nm'],
                    'rt_days': vp['rt_days'], 'rt_periods': vp['rt_periods'],
                    'arrival_offset_periods': vp['arrival_offset_periods'],
                    'arrival_offset_days': vp['arrival_offset_days'],
                    'fuel_cost': vp['fuel_cost'], 'port_charges': vp['port_charges'],
                    'hire_cost': vp['hire_cost'], 'fixed_cost': vp['fixed_cost']})
        manifest_k[k] = {'stage2_folder': os.path.relpath(folder, _SCRIPT_DIR),
                         'stage2_manifest_sha256': _sha256_file(s2_manifest_path),
                         'stage2_status': s2_status, 'stage2_mip_gap': s2_gap,
                         'charter_pool': [v['id'] for v in charter_pool],
                         'voyage_parameters': voyage_params,
                         'solve': {'status': sol['status'], 'objective_incumbent': sol.get('obj_val'),
                                   'objective_bound': sol.get('obj_bound'), 'mip_gap': sol['gap'],
                                   'runtime_sec': sol['runtime'], 'sol_count': sol.get('sol_count')},
                         'summary_row': rows[-1]}

    # Consolidated workbook (main project directory)
    _write_sweep_workbook(rows, schedules, out_path)
    _write_manifest(manifest_path, {
        'stage': 'Stage 3 (sea-distance version)',
        'created_at_utc': _dt.datetime.now(_dt.timezone.utc).isoformat(timespec='seconds'),
        'script': os.path.basename(__file__),
        'script_sha256': _sha256_file(os.path.abspath(__file__)),
        'distance_csv_sha256': SEA_CSV_SHA256,
        'distance_source_sha256': SEA_META.get('source_sha256'),
        'environment': _environment_record(),
        'constants': {'PERIOD_DAYS': PERIOD_DAYS, 'TOTAL_DAYS': TOTAL_DAYS, 'T_MAX': T_MAX,
                      'KURS': KURS, 'HARGA_IFO': HARGA_IFO, 'HARGA_MDO': HARGA_MDO,
                      'CHC_RATE': CHC_RATE, 'BUFFER_TIME_PCT': BUFFER_TIME_PCT,
                      'VC_PREMIUM': VC_PREMIUM, 'STOCKOUT_PENALTY': STOCKOUT_PENALTY,
                      'TimeLimit_sec': 1200, 'MIPGap': 0.02},
        'workbook': os.path.basename(out_path),
        'per_k': manifest_k})
    print(f"[Manifest] Stage-3 run manifest written: {manifest_path}")
    print(f"\n[Excel] Consolidated workbook saved to: {out_path}")

    # Descriptive comparison (NOT a global-optimality claim)
    valid = [r for r in rows if r["Combined_Financial_Cost"] is not None]
    if valid:
        low = min(valid, key=lambda r: r["Combined_Financial_Cost"])
        print("\n" + "-" * 100)
        print(f"Lowest observed combined financial cost among evaluated k configurations: "
              f"k={low['k']} at Rp {low['Combined_Financial_Cost']:,.0f}.")
        print("This is a descriptive comparison of observed (partly time-limited) incumbents, "
              "NOT a global-optimality claim over k.")
        print("-" * 100)


if __name__ == '__main__':
    main()
