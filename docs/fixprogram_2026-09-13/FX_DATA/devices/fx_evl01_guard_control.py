#!/usr/bin/env python3
"""fx_evl01_guard_control.py — EVL-01 (c) end-to-end control on pod2 (read-only inputs). Committed before it is run.

The lead's stated red test for the guard, both halves, on the REAL A0 device (`/workspace/uplift_2026-09-11/w10_sleeve.py`,
sha b88e35a4, which SPEC section 7 pins and which is not a git file):

  RED    launching it without CAL is refused, and the refusal names the device.
  GREEN  launching it with CAL=log is allowed, and the arm it produces is BITWISE identical to the archived
         `r3k/arms/A0_PWR230k_s42.npz` in both `rec` and `W` — so the guard demonstrably changed nothing about the run.

Usage: python3 fx_evl01_guard_control.py <arms_dir> <out_receipt.json>
Exit 0 only if the refusal happened AND the allowed run reproduced the archived arm bitwise.
"""
import os, sys, json, time, subprocess
import numpy as np
ENV_WHITELIST = {"PATH", "HOME", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "PYTHONPATH"}
EXTRA = sorted(k for k in os.environ if k not in ENV_WHITELIST and k not in ("PWD", "SHLVL", "_", "OLDPWD", "LC_CTYPE"))
assert EXTRA == [], ("ENV WHITELIST VIOLATION", EXTRA)
os.nice(19)
ARMS, OUT = sys.argv[1], sys.argv[2]
for p in os.environ["PYTHONPATH"].split(":"): sys.path.insert(0, p)
import cal_guard as G
import tradability as T

W = "/workspace"
DEV = f"{W}/uplift_2026-09-11/w10_sleeve.py"
HC = f"{W}/review_scratch/health_check"; R3K = f"{W}/uplift_2026-09-11/r3k"
K3 = f"{W}/review_scratch/king_v4/SLOW_v3_on_v4axis.npy"
ARCH = f"{R3K}/arms/A0_PWR230k_s42.npz"
DEVDIR = f"{W}/fx_data_2026-09-13/a0dev"
TAG = "GUARDCTL_PWR230k_s42"
def utc(t): return time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(int(t)))
FAILS = []; CHECKS = []
def check(n, ok, d=None):
    CHECKS.append({"check": n, "ok": bool(ok), **({"detail": d} if d is not None else {})})
    if not ok: FAILS.append(n)

rec = {"device": "fx_evl01_guard_control.py", "self_sha256": T.guarded_sha256(os.path.abspath(__file__)),
       "guard_sha256": T.guarded_sha256(os.path.join(os.environ["PYTHONPATH"].split(":")[0], "cal_guard.py")),
       "a0_device": DEV, "a0_device_sha256": T.guarded_sha256(DEV), "archived_arm": ARCH,
       "archived_arm_sha256": T.guarded_sha256(ARCH), "numpy": np.__version__,
       "env": {k: os.environ[k] for k in sorted(os.environ)}, "utc_start": utc(time.time())}
man = G.load_manifest()
rec["manifest_sha256"] = G.MANIFEST_SHA256
check("G0.a0_device_is_pinned_by_the_manifest", G.requires_cal(DEV, manifest=man), {"sha": rec["a0_device_sha256"][:16]})

BOOK_WL = {"PATH", "HOME", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
           "LEGS", "CAL", "WRULE", "LOOK", "MEMBERS_TOPN", "FTRIM", "PHI", "UMASK_SCOPE", "UMASK_NPZ",
           "SLOW_NPY", "FSEED", "FPRED", "COSTB_JSON", "OUT_TAG"}
BASE = {"PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin", "HOME": "/root",
        "OMP_NUM_THREADS": "3", "OPENBLAS_NUM_THREADS": "3", "MKL_NUM_THREADS": "3",
        "LEGS": "101", "WRULE": "msharpe", "LOOK": "900", "MEMBERS_TOPN": "829", "FTRIM": "zero", "PHI": "0.45",
        "UMASK_SCOPE": "m1", "UMASK_NPZ": f"{HC}/masks/umask_UPIT_CRYPTO.npz", "SLOW_NPY": K3,
        "FSEED": "42", "FPRED": "f10_A0_s42.npy", "COSTB_JSON": f"{R3K}/costb_PWR_G230k.json", "OUT_TAG": TAG}

# ---- RED half: no CAL ----
try:
    G.check_launch(DEV, dict(BASE), whitelist=BOOK_WL)
    check("G1.refuses_the_launch_without_CAL", False, {"note": "the guard allowed a launch with no CAL"})
    msg = None
except G.CalGuardError as e:
    msg = str(e)
    check("G1.refuses_the_launch_without_CAL", True, None)
    check("G1b.refusal_names_the_device", "w10_sleeve.py" in msg, {"message": msg[:240]})
    check("G1c.refusal_names_the_ruling", "EVL-01" in msg, None)
rec["refusal_message"] = msg

# ---- also refuse when CAL is set but not declared in the whitelist ----
try:
    G.check_launch(DEV, dict(BASE, CAL="log"), whitelist=BOOK_WL - {"CAL"})
    check("G2.refuses_when_CAL_is_not_in_the_whitelist", False)
except G.CalGuardError as e:
    check("G2.refuses_when_CAL_is_not_in_the_whitelist", "enumerated env whitelist" in str(e), {"message": str(e)[:200]})

# ---- GREEN half: CAL=log, allowed, and the run must reproduce the archived arm bitwise ----
env = dict(BASE, CAL="log")
o = G.check_launch(DEV, env, whitelist=BOOK_WL)
check("G3.allows_the_launch_with_CAL_log", bool(o["ok"] and o["requires_cal"] and o["cal"] == "log"), o)
src = os.path.join(DEVDIR, "probe_artifacts", "w10_ablation_series_%s.npz" % TAG)
if os.path.exists(src): os.remove(src)
t0 = time.time()
p = subprocess.run(["nice", "-n", "19", "/workspace/venv/bin/python", DEV], cwd=DEVDIR, env=env,
                   capture_output=True, text=True)
rec["run"] = {"rc": p.returncode, "seconds": round(time.time() - t0, 1), "tail": p.stdout.strip().splitlines()[-1][:200] if p.stdout.strip() else ""}
check("G4.the_allowed_run_exits_0", p.returncode == 0, {"rc": p.returncode, "stderr": p.stderr[-300:]})
if p.returncode == 0 and os.path.exists(src):
    Z = np.load(src, allow_pickle=True); A = np.load(ARCH, allow_pickle=False)
    r_ok = np.asarray(Z["d30_n2_c42_rec"], np.float64).tobytes() == np.asarray(A["rec"], np.float64).tobytes()
    w_ok = np.asarray(Z["d30_n2_c42_W"]).tobytes() == np.asarray(A["W"]).tobytes()
    check("G5.rec_bitwise_equals_the_archived_A0", r_ok, None)
    check("G6.W_bitwise_equals_the_archived_A0", w_ok, None)
    cfg = json.loads(str(Z["config_json"])); rec["config_CAL"] = cfg.get("CAL")
    check("G7.the_run_recorded_CAL_log", cfg.get("CAL") == "log", {"CAL": cfg.get("CAL")})
    os.remove(src)
else:
    check("G5.rec_bitwise_equals_the_archived_A0", False, {"note": "no artifact produced"})
rec["checks"] = CHECKS; rec["n_failed"] = len(FAILS); rec["failed"] = FAILS
rec["utc_end"] = utc(time.time())
json.dump(rec, open(OUT, "w"), indent=1)
print("FX_EVL01_GUARD_CONTROL_DONE", json.dumps({"failed": len(FAILS), "checks": len(CHECKS)}), flush=True)
sys.exit(1 if FAILS else 0)
