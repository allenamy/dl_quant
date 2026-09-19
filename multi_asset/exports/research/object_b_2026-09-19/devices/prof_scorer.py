#!/usr/bin/env python3
"""Profile one P2 scoring anchor (lead request 14:4xZ; no behaviour change, measurement only). Replicates b_scorer.worker for one anchor in a
private sandbox (/dev/shm/object_b_prof), timing the worker-side steps and the scorer device (python -m cProfile), then re-runs the device's two
pipeline children (dlw_features.py; f8_higher_order_features.build) under cProfile on the very inputs the device wrote, and checks that the
profiled score equals the A0_main P2 score of that anchor bitwise. Writes receipts/PROF_SCORER.json.
usage: env -i PATH=/usr/bin:/bin HOME=/root LC_CTYPE=C.UTF-8 nice -n 10 /workspace/venv/bin/python -B prof_scorer.py [ISO anchor]"""
import os, sys, json, time, shutil, subprocess, pstats, io, calendar
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import b_lib as BL
import b_driver as BD
import b_scorer as BS

R = BD.R; PY = BD.VENV_PY
A_iso = sys.argv[1] if len(sys.argv) > 1 else "2023-06-01T00:00:00Z"
A = calendar.timegm(time.strptime(A_iso, "%Y-%m-%dT%H:%M:%SZ"))
T = {}; t0 = time.time()
G = BD.Globals(load_cache=True); T["globals_load_s"] = round(time.time() - t0, 2)
P = BS.load_p1(f"{R}/work/A0_main/P1"); i = int(np.where(P["anchor"] == A)[0][0]); Y = BL.f10_fold_for(A, G.f10)
fea_src, reader_src, man = BD.stage_sources()
root = "/dev/shm/object_b_prof/w0"; shutil.rmtree(root, ignore_errors=True)
t = time.time(); ws = BL.make_sandbox(root, fea_src, BD.SRC["bundle_config"][0], PY); T["sandbox_s"] = round(time.time() - t, 3)
BL.clear_mini(f"{ws}/fea171"); shutil.copy2(G.f10[Y]["np"], f"{ws}/fea171/f10_live_s42_np.npz")
t = time.time(); live = G.live_names(A); lmask = np.zeros(829, bool); lmask[[G.col[s] for s in live]] = True
ts, cd = G.cache_tail(A, lmask); T["cache_tail_s"] = round(time.time() - t, 3)
t = time.time(); np.savez(f"{ws}/state/rolling.npz", ts=ts, data=cd); T["savez_rolling_s"] = round(time.time() - t, 3); del cd
pm, aux = BS.p1_inputs(P, i, G.SYMS, A)
json.dump(aux, open(f"{ws}/state/aux.json", "w")); json.dump({"king": [], "rev24": [], "fund": []}, open(f"{ws}/state/leg_returns_live.json", "w"))
out = f"{root}/score.npz"
env = {"PATH": "/usr/bin:/bin", "HOME": root, "LC_CTYPE": "C.UTF-8", "WIDE_SHADOW_HOME": ws, "F10_SCORE_OUT": out,
       "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"}
t = time.time()
r = subprocess.run([PY, "-B", "-m", "cProfile", "-o", f"{root}/device.prof", f"{HERE}/f10_scorer_3520d363.py"], cwd=f"{ws}/fea171", env=env,
                   capture_output=True, text=True)
T["device_total_s"] = round(time.time() - t, 3); assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
dev_log = r.stdout.strip().splitlines()
z = np.load(out); f10 = z["f10_pm"].astype(np.float64)
ref_all = {}
for f in os.listdir(f"{R}/work/A0_main/p2"):
    if f.startswith("shard_") and f.endswith(".npz") and not f.endswith(".tmp.npz"): ref_all.update(BS.as_dict(f"{R}/work/A0_main/p2/{f}"))
same = None
if A in ref_all: same = bool(np.array_equal(ref_all[A]["f10"], f10, equal_nan=True) and np.array_equal(ref_all[A]["pm"], pm))


def top(prof, n=18):
    s = io.StringIO(); ps = pstats.Stats(prof, stream=s); ps.sort_stats("cumulative").print_stats(n); return s.getvalue().splitlines()[:n + 12]


# the device's two pipeline children, re-run under cProfile on the inputs the device itself wrote (mini/ as left by the device)
MINI = f"{ws}/fea171/mini"; HERE_F = f"{ws}/fea171"
cenv = dict(env); cenv.update({"F171_CACHE": f"{MINI}/cache.npz", "F171_TARGETS": f"{MINI}/data/dlw_targets.npz", "F171_OUT": MINI,
                               "F171_FEA82": f"{MINI}/data/dlw_fea82.npz", "F171_PANEL": f"{HERE_F}/xfer_panel_live.npz"})
t = time.time(); r1 = subprocess.run([PY, "-m", "cProfile", "-o", f"{root}/dlw.prof", f"{HERE_F}/dlw_features.py"], env=cenv, capture_output=True, text=True, cwd=HERE_F)
T["child_dlw_features_s"] = round(time.time() - t, 3); assert r1.returncode == 0, r1.stderr[-1500:]
t = time.time()
r2 = subprocess.run([PY, "-c", f"import cProfile,os,sys; sys.path.insert(0,'{HERE_F}'); os.chdir('{HERE_F}'); import f8_higher_order_features as m; cProfile.run('m.build()', '{root}/f8.prof')"],
                    env=cenv, capture_output=True, text=True)
T["child_f8_build_s"] = round(time.time() - t, 3); assert r2.returncode == 0, r2.stderr[-1500:]
t = time.time(); r3 = subprocess.run([PY, "-c", "import numpy, scipy.stats, scipy.special"], env=cenv, capture_output=True, text=True); T["python_start_numpy_scipy_import_s"] = round(time.time() - t, 3)
doc = {"anchor": A_iso, "fold": Y, "members": int(len(pm)), "timings_s": T, "device_log": dev_log, "profiled_score_equals_A0_main_P2": same,
       "device_top_cumulative": top(f"{root}/device.prof"), "dlw_features_top_cumulative": top(f"{root}/dlw.prof"), "f8_build_top_cumulative": top(f"{root}/f8.prof"),
       "self_sha256": BL.sha(os.path.abspath(__file__)), "utc": BL.iso(time.time())}
json.dump(doc, open(f"{R}/receipts/PROF_SCORER.json", "w"), indent=1)
print(json.dumps({k: doc[k] for k in ("anchor", "fold", "members", "timings_s", "profiled_score_equals_A0_main_P2")}), flush=True)
for k in ("device_top_cumulative", "dlw_features_top_cumulative", "f8_build_top_cumulative"):
    print("==", k); print("\n".join(doc[k]))
shutil.rmtree("/dev/shm/object_b_prof", ignore_errors=True)
