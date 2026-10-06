#!/usr/bin/env python3
# =============================================================================
# run_seadist_ksweep.py: runs Stages 1 and 2 (mirp_option_c_seadist.py) for
# K = 2..9 with the uniform solver budget used for the reported results
# (TIME_LIMIT_SEC = 7200 s per K, MIPGap 2%).
#
# Results go to OptionC_k{K}_SeaDist_Results/. The runner refuses to start if
# any of these folders already holds files, so earlier results are never
# overwritten.
#
# Stage 3 is run separately afterwards:
#     python supplementary_charter_milp_seadist_sweep.py
#
# A full sweep takes about 8 x 2 hours of solver time for Stage 2 and about
# 8 x 20 minutes for Stage 3 on the reference machine (see README).
# =============================================================================
import os
import sys
import subprocess
import time
import hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
K_VALUES = [2, 3, 4, 5, 6, 7, 8, 9]
SEA_DISTANCE_CSV = os.path.join(HERE, "data", "sea_distance_matrix_nm.csv")
EXPECTED_SEA_CSV_SHA256 = "fdc433907aeb90247ff5fa44add3f569cac7767d57a3437f4d3b5f4bfbc54dfe"


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _preflight():
    if not os.path.exists(SEA_DISTANCE_CSV) or _sha256(SEA_DISTANCE_CSV) != EXPECTED_SEA_CSV_SHA256:
        print("[FATAL] sea-distance CSV missing or checksum mismatch", file=sys.stderr)
        sys.exit(2)
    for k in K_VALUES:
        d = os.path.join(HERE, f"OptionC_k{k}_SeaDist_Results")
        if os.path.isdir(d) and os.listdir(d):
            print(f"[FATAL] {d} already holds files; refusing to overwrite. Nothing was run.",
                  file=sys.stderr)
            sys.exit(2)


def main():
    _preflight()
    for k in K_VALUES:
        env = dict(os.environ, K_CLUSTERS=str(k))
        print("\n" + "=" * 78)
        print(f"  Stage 1 + Stage 2   k = {k}   (TIME_LIMIT = 7200 s)")
        print("=" * 78, flush=True)
        t0 = time.time()
        proc = subprocess.run([sys.executable, os.path.join(HERE, "mirp_option_c_seadist.py")],
                              env=env)
        rc = proc.returncode
        print(f"  [k={k}] return code: {rc} | wall time: {time.time()-t0:,.0f} s", flush=True)
        if rc != 0:
            print(f"\n[FATAL] k={k} run failed (return code {rc}); stopping the sweep.",
                  file=sys.stderr, flush=True)
            sys.exit(rc)
    print("\nStage-2 sweep complete. Next: python supplementary_charter_milp_seadist_sweep.py")


if __name__ == "__main__":
    main()
