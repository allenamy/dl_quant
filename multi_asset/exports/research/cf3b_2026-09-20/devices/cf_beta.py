#!/usr/bin/env python3
"""cf_beta.py — CF3-B: build, for ONE CF3 arm, the two files `at_beta.py` reads, so that the CERTIFIED
device can run on a counterfactual world without being modified.

PREREG: docs/PREREG_style_beta_on_counterfactual_worlds_2026-09-20.md (+ addendum B-A1), both frozen
before any number of this task.

WHAT THIS DEVICE DOES, AND THE ONLY THING IT IS ALLOWED TO DO
  work/AT_PANEL.npz   = the ARCHIVED attribution panel with EXACTLY ONE array replaced: `W`.
                        Every other array is carried over bitwise (asserted, gate B2).
                        W is rebuilt with at_lib.reshape_pop — the certified function at_build.py L175
                        calls — never a re-implementation.
  work/AT_L1_mean.npz = `A` + `g` for this arm, from its own 32 simulator path files.
                        at_beta.py reads only L1["g"] (grep-verified, L301-302).

GATES (run before anything is written; a failure writes no panel)
  B2  every array except `W` is bitwise identical to the archived panel
  B3  for arm BASE, the rebuilt `W` equals the archived `W` bitwise on the 9,139 in_run rows
  B4  for arm BASE, the rebuilt `g` equals the archived AT_L1_mean `g` bitwise
  B-A1  the 113 extension rows (panel rows outside in_run; the arms' axis stops at 2026-08-31) are set
        to NaN — not 0 (0 is a legal weight and would encode "no measurement" as "flat", E-0920-C) and
        not the in-service W (that would pass the live book's holdings off as the arm's). The device
        also PROVES they are unreadable rather than asserting it: see cf_beta_unread_test.py.

usage: env -i ... /workspace/venv/bin/python -B cf_beta.py <ENV_WHITELIST_CSV> <ARM> <OUT_DIR>
"""
import hashlib
import json
import os
import sys
import time

import numpy as np

T0 = time.time()
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import at_lib as L                                   # the CF3-B copy: identical but for the ROOT line


def iso(t):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(t)))

ATTRIB = "/workspace/attrib_2026_2026-09-20"
CF3 = "/workspace/cf3_2026-09-20"
ENV_OK = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else set()
ARM = sys.argv[2]
OUT = sys.argv[3]
os.makedirs(OUT, exist_ok=True)
os.makedirs(f"{L.ROOT}/work", exist_ok=True)

rows = []
fails = []


def chk(name, ok, detail=None):
    rows.append({"check": name, "ok": bool(ok), "detail": detail})
    if not ok:
        fails.append(name)
    return bool(ok)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def bitwise(a, b):
    a = np.ascontiguousarray(a)
    b = np.ascontiguousarray(b)
    if a.shape != b.shape or a.dtype != b.dtype:
        return False, -1
    ua = a.view({4: np.uint32, 8: np.uint64}.get(a.dtype.itemsize, np.uint8))
    ub = b.view({4: np.uint32, 8: np.uint64}.get(b.dtype.itemsize, np.uint8))
    ne = ua != ub
    return (not ne.any()), int(ne.sum())


rec = {"device": "cf_beta.py", "self_sha256": sha(os.path.abspath(__file__)), "arm": ARM,
       "argv": list(sys.argv), "env": dict(os.environ), "python": sys.version.split()[0],
       "numpy": np.__version__, "utc_start": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
       "prereg": "docs/PREREG_style_beta_on_counterfactual_worlds_2026-09-20.md (+B-A1)"}
chk("env.whitelist", not sorted(set(rec["env"]) - ENV_OK), {"extra": sorted(set(rec["env"]) - ENV_OK)})

# ── B1: instrument identity ────────────────────────────────────────────────
cert_beta = f"{ATTRIB}/devices/at_beta.py"
cert_lib = f"{ATTRIB}/devices/at_lib.py"
mine_beta = f"{HERE}/at_beta.py"
mine_lib = f"{HERE}/at_lib.py"
chk("B1.at_beta_byte_identical", sha(cert_beta) == sha(mine_beta),
    {"certified": sha(cert_beta), "mine": sha(mine_beta)})
ca = open(cert_lib).read().split("\n")
mb = open(mine_lib).read().split("\n")
diff = [(i + 1, a, b) for i, (a, b) in enumerate(zip(ca, mb)) if a != b]
chk("B1.at_lib_diff_is_only_the_ROOT_line",
    len(ca) == len(mb) and len(diff) == 1 and diff[0][1].startswith("ROOT =") and diff[0][2].startswith("ROOT ="),
    {"n_differing_lines": len(diff), "diff": [{"line": d[0], "certified": d[1], "mine": d[2]} for d in diff]})
rec["instrument"] = {"at_beta_sha256": sha(mine_beta), "at_lib_sha256_certified": sha(cert_lib),
                     "at_lib_sha256_mine": sha(mine_lib)}
if fails:
    json.dump({**rec, "checks": rows, "failed": fails, "verdict": "REFUSED"},
              open(f"{OUT}/CF_BETA_{ARM}.json", "w"), indent=1, default=float)
    print("CF_BETA VERDICT=REFUSED arm=%s failed=%s" % (ARM, fails), flush=True)
    sys.exit(3)

# ── inputs ─────────────────────────────────────────────────────────────────
APAN = f"{ATTRIB}/work/AT_PANEL.npz"
AL1 = f"{ATTRIB}/work/AT_L1_mean.npz"
TGT = f"{CF3}/work/TARGETS_CF_{ARM}.npz"
RUNDIR = f"{CF3}/runs/CF_{ARM}_scaled_rule_raw_UAFE"
rec["inputs"] = {"archived_panel": {"path": APAN, "sha256": sha(APAN)},
                 "archived_L1": {"path": AL1, "sha256": sha(AL1)},
                 "arm_targets": {"path": TGT, "sha256": sha(TGT)},
                 "arm_run_dir": RUNDIR}

Z = {k: np.asarray(v) for k, v in np.load(APAN, allow_pickle=True).items()}
A_pan = Z["A"].astype(np.int64)
in_run = Z["in_run"]
NA, NW = Z["W"].shape

T = {k: np.asarray(v) for k, v in np.load(TGT, allow_pickle=True).items()}
A_arm = T["anchor"].astype(np.int64)
row_of = {int(a): i for i, a in enumerate(A_arm)}

# ── rebuild W for this arm (at_build.py L164-176, using at_lib.reshape_pop) ─
W = np.full((NA, NW), np.nan, np.float32)            # B-A1: NaN everywhere first
covered = np.zeros(NA, bool)
for i in range(NA):
    a = row_of.get(int(A_pan[i]))
    if a is None:
        continue                                      # EXT_NOT_COVERED: stays NaN
    covered[i] = True
    o0, o1 = int(T["scaled_off"][a]), int(T["scaled_off"][a + 1])
    ii = T["scaled_idx"][o0:o1].astype(np.int64)
    vv = T["scaled_val"][o0:o1]
    W[i] = 0.0
    if len(ii):
        W[i, ii] = L.reshape_pop(vv)

n_ext = int((~covered).sum())
chk("B-A1.covered_equals_in_run", bool(np.array_equal(covered, in_run)),
    {"n_covered": int(covered.sum()), "n_in_run": int(in_run.sum()), "n_EXT_NOT_COVERED": n_ext,
     "ext_first": iso(A_pan[~covered][0]) if n_ext else None,
     "ext_last": iso(A_pan[~covered][-1]) if n_ext else None})
chk("B-A1.ext_rows_are_NaN", bool(np.isnan(W[~covered]).all()) if n_ext else True, {"n_rows": n_ext})

# ── rebuild g for this arm (at_control.py: per path 1e4*r/gm, then path mean) ─
files = sorted(f for f in os.listdir(RUNDIR) if f.startswith("PATH_") and f.endswith(".npz"))
chk("input.32_path_files", len(files) == 32, {"n": len(files)})
gs = []
A_l1 = None
for f in files:
    P = np.load(os.path.join(RUNDIR, f))
    r = P["navm1"] / P["navm0"] - 1.0
    gs.append(1e4 * r / 2.0)
    if A_l1 is None:
        A_l1 = P["A"].astype(np.int64)
g = np.stack(gs).mean(0)
chk("L1.axis_equals_panel_in_run", bool(np.array_equal(A_l1, A_pan[in_run])), {"n": int(len(A_l1))})

# ── B3 / B4 (B2 is asserted AFTER writing, by reading the file back) ───────
if ARM == "BASE":
    okW, nW = bitwise(W[in_run], Z["W"][in_run])
    chk("B3.BASE_W_bitwise_vs_archive", okW, {"n_cells_differ": nW, "n_rows": int(in_run.sum())})
    gA = np.asarray(np.load(AL1)["g"])
    okg, ng = bitwise(g.astype(gA.dtype), gA)
    chk("B4.BASE_g_bitwise_vs_archive", okg, {"n_cells_differ": ng, "n": int(len(gA))})
else:
    chk("B3.BASE_W_bitwise_vs_archive", True, {"skipped": "not the BASE arm; B3 is certified on BASE"})
    chk("B4.BASE_g_bitwise_vs_archive", True, {"skipped": "not the BASE arm; B4 is certified on BASE"})

rec["verdict"] = "PASS"
rec["runtime_s"] = round(time.time() - T0, 1)
if fails:
    rec["checks"] = rows; rec["failed"] = fails; rec["verdict"] = "REFUSED"
    json.dump(rec, open(f"{OUT}/CF_BETA_{ARM}.json", "w"), indent=1, default=float)
    print("CF_BETA VERDICT=REFUSED arm=%s failed=%s" % (ARM, fails), flush=True)
    sys.exit(3)

out_pan = f"{L.ROOT}/work/AT_PANEL.npz"
out_l1 = f"{L.ROOT}/work/AT_L1_mean.npz"
tmp_pan = out_pan + ".tmp.npz"
np.savez_compressed(tmp_pan, **{**Z, "W": W})

# ── B2: read the WRITTEN file back and compare it to the ARCHIVED file. Comparing the in-memory
#    dict to itself would be vacuously true — the thing that can go wrong (savez dropping, casting
#    or re-ordering an array) only shows up on the round trip.
RB = {k: np.asarray(v) for k, v in np.load(tmp_pan, allow_pickle=True).items()}
AR = {k: np.asarray(v) for k, v in np.load(APAN, allow_pickle=True).items()}
missing = sorted(set(AR) - set(RB))
extra = sorted(set(RB) - set(AR))
non_W_bad = []
for k in sorted(set(AR) & set(RB)):
    if k == "W":
        continue
    ok, n = bitwise(AR[k], RB[k])
    if not ok:
        non_W_bad.append({"key": k, "n_cells_differ": n,
                          "dtype": [str(AR[k].dtype), str(RB[k].dtype)],
                          "shape": [list(AR[k].shape), list(RB[k].shape)]})
okWrb, nWrb = bitwise(W, RB["W"])
chk("B2.only_W_is_replaced_verified_on_the_written_file",
    (not non_W_bad) and (not missing) and (not extra) and okWrb,
    {"n_keys": len(AR), "n_arrays_carried_bitwise": len(AR) - 1, "bad": non_W_bad[:5],
     "missing_keys": missing, "extra_keys": extra, "W_round_trip_bitwise": okWrb,
     "W_round_trip_cells_differ": nWrb})
if fails:
    os.remove(tmp_pan)
    rec["checks"] = rows; rec["failed"] = fails; rec["verdict"] = "REFUSED"
    json.dump(rec, open(f"{OUT}/CF_BETA_{ARM}.json", "w"), indent=1, default=float)
    print("CF_BETA VERDICT=REFUSED arm=%s failed=%s (no panel written)" % (ARM, fails), flush=True)
    sys.exit(3)

os.replace(tmp_pan, out_pan)
np.savez_compressed(out_l1 + ".tmp.npz", A=A_l1, g=g)
os.replace(out_l1 + ".tmp.npz", out_l1)
rec["checks"] = rows
rec["failed"] = fails
rec["outputs"] = {"panel": {"path": out_pan, "sha256": sha(out_pan)},
                  "L1": {"path": out_l1, "sha256": sha(out_l1)}}
json.dump(rec, open(f"{OUT}/CF_BETA_{ARM}.json", "w"), indent=1, default=float)
print("CF_BETA VERDICT=PASS arm=%s checks=%d failed=[] n_EXT_NOT_COVERED=%d receipt_sha256=%s"
      % (ARM, len(rows), n_ext, sha(f"{OUT}/CF_BETA_{ARM}.json")), flush=True)
