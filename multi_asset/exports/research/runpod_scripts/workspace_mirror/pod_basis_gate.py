"""§25 basis 特征门 @pod: premidx zips → 3 因果特征 → 慢引擎双跑重训 → 三门判(判据已冻结).
不动 shadow_bundle(过门=进 09-01 v2 世代).
"""
import os, io, csv, json, time, glob, zipfile
import numpy as np
import sys; sys.path.insert(0, "/workspace")
from scipy.stats import rankdata, spearmanr
MT = np.load("/workspace/data/wide_fea_v2ext_meta.npz", allow_pickle=True)
E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; y4 = MT["y4"]; qvk = MT["qvk"]
names = [str(n) for n in MT["names"]]
yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts])
nA = len(E_ts); NW = 829
FEA = np.load("/workspace/data/wide_fea_v2ext.npy")
PW = np.load("/workspace/data/wide_panel_4h_v2ext.npz", allow_pickle=True)
syms = [str(s) for s in PW["symbols"]]
sym_idx = {s: j for j, s in enumerate(syms)}
anchor_s = E_ts

# ── premidx: 月度+daily zips → 逐bar close → 锚对齐 3 特征 ──
HL = 3 * 86400.0
b_now = np.full((nA, NW), np.nan, np.float32)
b_ema = np.full((nA, NW), np.nan, np.float32)
b_chg = np.full((nA, NW), np.nan, np.float32)
n_px = 0
for base_dir in ("/workspace/wide_multisrc/premidx", ):
    for sym_dir in sorted(glob.glob(base_dir + "/*")):
        s = os.path.basename(sym_dir)
        j = sym_idx.get(s)
        if j is None: continue
        rows = []
        zps = sorted(glob.glob(sym_dir + "/*.zip")) + sorted(glob.glob(f"/workspace/wide_multisrc/premidx_daily/{s}/*.zip"))
        for zp in zps:
            try:
                zf = zipfile.ZipFile(zp)
                with zf.open(zf.namelist()[0]) as fh:
                    rd = csv.reader(io.TextIOWrapper(fh))
                    for row in rd:
                        if not row or not row[0].strip().lstrip("-").isdigit():
                            continue
                        try:
                            rows.append((int(row[0]) // 1000 + 300, float(row[4])))  # close_time=open+5m, close px
                        except Exception:
                            continue
            except Exception:
                continue
        if len(rows) < 1000: continue
        rows.sort()
        ded = {}
        for t_, v_ in rows: ded[t_] = v_
        ft = np.array(sorted(ded), np.int64)
        fv = np.array([ded[t] for t in ft], np.float64)
        ema = np.full(len(fv), np.nan)
        acc, prev_t = None, None
        for k in range(len(fv)):
            if acc is None: acc = fv[k]
            else:
                a = 1 - 0.5 ** (max(ft[k] - prev_t, 1) / HL)
                acc = acc + a * (fv[k] - acc)
            prev_t = ft[k]; ema[k] = acc
        pos = np.searchsorted(ft, anchor_s, side="right") - 1
        okp = pos >= 0
        stale = okp & ((anchor_s - np.where(okp, ft[np.maximum(pos, 0)], 0)) > 6 * 3600)
        b_now[okp, j] = fv[pos[okp]].astype(np.float32)
        b_ema[okp, j] = ema[pos[okp]].astype(np.float32)
        pos24 = np.searchsorted(ft, anchor_s - 86400, side="right") - 1
        ok24 = okp & (pos24 >= 0)
        b_chg[ok24, j] = (fv[pos[ok24]] - fv[pos24[ok24]]).astype(np.float32)
        for arr in (b_now, b_ema, b_chg):
            arr[stale, j] = np.nan
        n_px += 1
print(f"premidx 币数 {n_px}", flush=True)
if n_px < 300:
    print("BASIS_FAIL data_coverage", flush=True); sys.exit(3)

keep = [k for k, nm in enumerate(names) if not (nm.startswith("ret5_sum_48") or nm.startswith("ret5_sum_288"))]
def sp(a, b):
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 30: return np.nan
    r = spearmanr(a[ok], b[ok]); return r.correlation if hasattr(r, "correlation") else r[0]
rows_X, rows_Xb, rows_y, rows_a = [], [], [], []
for i in range(nA):
    m = members[i]
    yv = y4[i, m]; ok = np.isfinite(yv)
    if ok.sum() < 50: continue
    rr = rankdata(yv[ok]) / max(ok.sum() - 1, 1) - 0.5
    base = FEA[i, m[ok]][:, keep].astype(np.float32)
    ext = np.stack([np.nan_to_num(b_now[i, m[ok]], nan=0), np.nan_to_num(b_ema[i, m[ok]], nan=0),
                    np.nan_to_num(b_chg[i, m[ok]], nan=0)], 1).astype(np.float32)
    rows_X.append(base); rows_Xb.append(np.concatenate([base, ext], 1))
    rows_y.append(rr.astype(np.float32)); rows_a.append(np.full(ok.sum(), i, np.int32))
X0 = np.concatenate(rows_X); X1 = np.concatenate(rows_Xb)
Y = np.concatenate(rows_y); A = np.concatenate(rows_a)
YRA = yrs[A]
import lightgbm as lgb
def fold_ics(X):
    out = {}
    PRED = np.full((nA, NW), np.nan, np.float32)
    for YV in (2024, 2025, 2026):
        tr = YRA < YV; te = YRA == YV
        if te.sum() == 0: continue
        g = lgb.LGBMRegressor(n_estimators=400, learning_rate=0.05, num_leaves=63,
                              subsample=0.8, colsample_bytree=0.8, n_jobs=100, verbose=-1).fit(X[tr], Y[tr])
        pv = g.predict(X[te]); a_te = A[te]
        ics = []
        for a in np.unique(a_te):
            selr = a_te == a; m = members[a]; okm = np.isfinite(y4[a, m])
            PRED[a, m[okm]] = pv[selr]
            ics.append(sp(pv[selr], y4[a, m[okm]]))
        out[str(YV)] = float(np.nanmean(ics))
    return out, PRED
res = {"runs": []}
gate_ic = []
for run in (1, 2):
    ic0, _ = fold_ics(X0)
    ic1, P1 = fold_ics(X1)
    d2526 = ((ic1["2025"] - ic0["2025"]) + (ic1["2026"] - ic0["2026"])) / 2
    worst = min(ic1["2025"] - ic0["2025"], ic1["2026"] - ic0["2026"])
    ok_run = d2526 >= 0.0015 and worst >= -0.001
    res["runs"].append({"base": ic0, "basis": ic1, "d2526": round(d2526, 4), "worst": round(worst, 4), "pass": ok_run})
    gate_ic.append(ok_run)
    print(f"[run{run}] base {ic0} basis {ic1} Δ2526 {d2526:+.4f} worst {worst:+.4f} {'PASS' if ok_run else 'FAIL'}", flush=True)
    if run == 1 and not ok_run:
        break  # 首跑不过, 双跑门已不可能全过
res["gate_ic_double"] = all(gate_ic) and len(gate_ic) == 2
json.dump(res, open("/workspace/basis_gate.json", "w"), indent=1)
print(f"BASIS_GATE_{'PASS_IC' if res['gate_ic_double'] else 'FAIL'}", flush=True)
print("BASIS_DONE", flush=True)
