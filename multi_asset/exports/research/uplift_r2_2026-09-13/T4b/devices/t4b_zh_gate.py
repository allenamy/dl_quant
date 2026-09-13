#!/usr/bin/env python3
"""t4b_zh_gate.py — Mac, read-only on production (PREREG_T4b GATE ZH). Does the zero backfill of the V2MAIN funding panel's
history rows change the served V2MAIN input at the anchor being scored?
Takes the last anchor's inputs left by the served replay arm (replay_home_served/fea171: mini/cache.npz, mini/data/dlw_targets.npz,
xfer_panel_live.npz), and rebuilds the 82 + 89 features twice with the replay home's own copies of dlw_features.py and
f8_higher_order_features.py (sha-checked against ~/wide_shadow/fea171): (S) the served panel as is; (F) the same panel with every
history row of f_fund_ema and f_fund_now filled with non-zero values (last row untouched).
PASS <=> the scored anchor's 171-column rows are bitwise equal between S and F AND S equals the served replay's recorded X171 for that
anchor; RED capability: the history rows' funding columns must differ between S and F (the fill took effect).
Launch: env -i PATH=/usr/bin:/bin HOME=/Users/haosiyu /Users/haosiyu/wide_shadow/venv/bin/python -B devices/t4b_zh_gate.py <whitelist>"""
import os, sys, json, time, hashlib, shutil, subprocess
WHITE = set(x for x in sys.argv[1].split(",") if x) if len(sys.argv) > 1 else None
assert WHITE, "whitelist argv[1]"
assert sorted(k for k in os.environ if k not in WHITE) == [], ("ENV WHITELIST VIOLATION", sorted(os.environ))
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); T4B = os.path.dirname(HERE); PRIV = T4B + "/private"
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
_fr = open(T4B + "/receipts/PREREG_FREEZE_sha.txt").readline().split(); PREREG_SHA = _fr[2]; assert sha(T4B + "/PREREG_T4b_v2main_feature_skew_2026-09-13.md") == PREREG_SHA
RH = PRIV + "/replay_home_served/fea171"; LIVE = "/Users/haosiyu/wide_shadow/fea171"
for f in ("dlw_features.py", "f8_higher_order_features.py"): assert sha(f"{RH}/{f}") == sha(f"{LIVE}/{f}"), f
REC = list(np.load(PRIV + "/replay_rec_served.npy", allow_pickle=True)); last = REC[-1]; A = int(last["anchor"])
T9 = np.load(f"{RH}/mini/data/dlw_targets.npz", allow_pickle=True); assert int(T9["E_ts"].astype(np.int64)[-1]) == A
PY = "/Users/haosiyu/wide_shadow/venv/bin/python"; G = PRIV + "/zh_gate"; shutil.rmtree(G, ignore_errors=True)
P0 = np.load(f"{RH}/xfer_panel_live.npz"); ts = P0["ts"]; fe = P0["f_fund_ema"].copy(); fn = P0["f_fund_now"].copy()
assert int(ts[-1]) == A and (fe[:-1] == 0).all() and (fn[:-1] == 0).all()
nh = fe.shape[0] - 1; k = (np.arange(nh, dtype=np.float32)[:, None] + 1.0)
fe_f = fe.copy(); fn_f = fn.copy()
fe_f[:-1] = np.where(fe[-1][None, :] != 0, fe[-1][None, :] * (1 + 1e-3 * k), 1e-4 * k); fn_f[:-1] = np.where(fn[-1][None, :] != 0, fn[-1][None, :] * (1 - 1e-3 * k), -1e-4 * k)
OUTS = {}
for var, (a, b) in (("S", (fe, fn)), ("F", (fe_f, fn_f))):
    d = f"{G}/{var}"; os.makedirs(d + "/data"); os.makedirs(d + "/results"); os.makedirs(d + "/preds")
    shutil.copy2(f"{RH}/mini/data/dlw_targets.npz", d + "/data/dlw_targets.npz")
    np.savez(d + "/panel.npz", ts=ts, f_fund_ema=a, f_fund_now=b)
    env = {"PATH": "/usr/bin:/bin", "HOME": os.path.expanduser("~"), "PYTHONDONTWRITEBYTECODE": "1", "F171_CACHE": f"{RH}/mini/cache.npz", "F171_TARGETS": d + "/data/dlw_targets.npz",
           "F171_OUT": d, "F171_FEA82": d + "/data/dlw_fea82.npz", "F171_PANEL": d + "/panel.npz"}
    t0 = time.time()
    r1 = subprocess.run([PY, "-B", f"{RH}/dlw_features.py"], env=env, capture_output=True, text=True, cwd=RH); assert r1.returncode == 0, r1.stderr[-800:]
    r2 = subprocess.run([PY, "-B", "-c", f"import os,sys; sys.path.insert(0,'{RH}'); os.chdir('{RH}'); import f8_higher_order_features as m; m.build()"], env=env, capture_output=True, text=True); assert r2.returncode == 0, r2.stderr[-800:]
    F82 = np.load(d + "/data/dlw_fea82.npz", allow_pickle=True); F89 = np.load(d + "/data/f8_fea89.npz", allow_pickle=True)
    OUTS[var] = dict(X82=F82["X"], X89=F89["X"], pa=F82["pair_a"].astype(np.int64), ps=F82["pair_s"].astype(np.int64), wall_s=round(time.time() - t0, 1))
S, F = OUTS["S"], OUTS["F"]; a_i = int(len(T9["E_ts"]) - 1)
assert np.array_equal(S["pa"], F["pa"]) and np.array_equal(S["ps"], F["ps"])
rowA = S["pa"] == a_i; hist = ~rowA
XS = np.concatenate([S["X82"][rowA].astype(np.float32), S["X89"][rowA]], 1); XF = np.concatenate([F["X82"][rowA].astype(np.float32), F["X89"][rowA]], 1)
res = dict(anchor=A, anchor_rows=int(rowA.sum()), history_rows=int(hist.sum()),
           anchor_rows_bitwise_S_vs_F=bool(np.array_equal(XS, XF)), anchor_rows_S_vs_recorded_served=bool(np.array_equal(XS, last["combo_X171"]) and np.array_equal(S["ps"][rowA], last["combo_scol"])),
           red_history_col80_rows_differ=int((S["X82"][hist, 80] != F["X82"][hist, 80]).sum()), red_history_col81_rows_differ=int((S["X82"][hist, 81] != F["X82"][hist, 81]).sum()),
           history_non_fund_cols_bitwise=bool(np.array_equal(np.delete(S["X82"][hist], [80, 81], axis=1), np.delete(F["X82"][hist], [80, 81], axis=1)) and np.array_equal(S["X89"][hist], F["X89"][hist])),
           wall_s=dict(S=S["wall_s"], F=F["wall_s"]))
res["PASS"] = bool(res["anchor_rows_bitwise_S_vs_F"] and res["anchor_rows_S_vs_recorded_served"] and res["red_history_col80_rows_differ"] > 0)
RC = dict(self_sha256=sha(os.path.abspath(__file__)), prereg_sha256=PREREG_SHA, inputs={f"{RH}/mini/cache.npz": sha(f"{RH}/mini/cache.npz"), f"{RH}/xfer_panel_live.npz": sha(f"{RH}/xfer_panel_live.npz"),
          f"{RH}/mini/data/dlw_targets.npz": sha(f"{RH}/mini/data/dlw_targets.npz"), "dlw_features.py": sha(f"{RH}/dlw_features.py"), "f8_higher_order_features.py": sha(f"{RH}/f8_higher_order_features.py")},
          result=res, env=dict(whitelist=sorted(WHITE), actual={k: os.environ[k] for k in sorted(os.environ)}), built_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
json.dump(RC, open(T4B + "/receipts/RECEIPT_T4b_zh_gate.json", "w"), indent=1, default=str); print(json.dumps(res, indent=1))
assert res["PASS"], "GATE ZH FAIL"
