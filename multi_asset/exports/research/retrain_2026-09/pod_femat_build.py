"""fund 腿变体矩阵构建 @pod(PREREG_fundleg e888007fd6ae): A1..A5, splice 网格, 全因果。"""
import json, gzip, glob, zipfile, io, csv
import numpy as np
PW = np.load("/workspace/data/wide_panel_4h_v3splice.npz", allow_pickle=True)
ts = PW["ts"].astype(np.int64); syms = [str(s) for s in PW["symbols"]]
E1 = PW["f_fund_ema_v1"].astype(np.float64); NOW = PW["f_fund_now"].astype(np.float64)
nA, NW = E1.shape
def zc(M):
    out = np.full_like(M, np.nan)
    for i in range(M.shape[0]):
        v = M[i]; ok = np.isfinite(v)
        if ok.sum() >= 10:
            mu, sd = v[ok].mean(), v[ok].std()
            if sd > 0: out[i, ok] = (v[ok] - mu) / sd
    return out
def save(name, fe):
    np.savez_compressed(f"/workspace/femat_{name}.npz", ts=ts, symbols=np.array(syms), fe=fe.astype(np.float32))
    print(f"{name} saved finite {np.isfinite(fe).mean():.3f}", flush=True)
# A1
save("A1_v2cal", PW["f_fund_ema_v2"].astype(np.float32))
# A4/A5(面板算术)
D6 = np.full_like(E1, np.nan); D6[6:] = E1[6:] - E1[:-6]
save("A4_dmom", np.nan_to_num(zc(E1), nan=np.nan) + 0.1 * np.nan_to_num(zc(D6), nan=0.0))
save("A5_gap", np.nan_to_num(zc(E1), nan=np.nan) + 0.1 * np.nan_to_num(zc(NOW - E1), nan=0.0))
# A2/A3 事件重折(同 splice 解析)
HLs = {"A2_hl15": 1.5 * 86400.0, "A3_hl7d": 7 * 86400.0}
ALLOWED = np.array([1.0, 2.0, 4.0, 6.0, 8.0])
AUG = json.loads(gzip.open("/workspace/fund_aug.json.gz", "rt").read())
AUG_IV = {k: float(v) for k, v in (AUG.get("intervals") or {}).items() if v}
out = {k: np.full((nA, NW), np.nan, np.float32) for k in HLs}
anchor_s = ts
for j, s in enumerate(syms):
    rows = []
    for zp in sorted(glob.glob(f"/workspace/wide_multisrc/funding/{s}/*.zip")):
        try:
            zf = zipfile.ZipFile(zp)
            with zf.open(zf.namelist()[0]) as fh:
                rd = csv.reader(io.TextIOWrapper(fh))
                for row in rd:
                    if not row or not row[0].strip().isdigit() and "time" in row[0].lower(): continue
                    try:
                        t_ = int(row[0]); rate = float(row[-1]) if abs(float(row[-1])) < 0.2 else float(row[1])
                        iv = np.nan
                        if len(row) >= 3:
                            try:
                                c = float(row[1])
                                if 1 <= c <= 24 and abs(c - round(c)) < 1e-9 and abs(float(row[-1])) < 0.2: iv = c
                            except Exception: pass
                        rows.append((t_ // 1000, rate, iv))
                    except Exception: continue
        except Exception: continue
    for t_ms, rate in (AUG.get("rates") or {}).get(s, []):
        rows.append((int(t_ms) // 1000, float(rate), AUG_IV.get(s, np.nan)))
    if not rows: continue
    rows.sort(); ded = {}
    for t_, r_, i_ in rows:
        if t_ not in ded or np.isfinite(i_): ded[t_] = (r_, i_)
    ft = np.array(sorted(ded), np.int64)
    fr = np.array([ded[t][0] for t in ft]); fiv = np.array([ded[t][1] for t in ft])
    dt_h = np.round(np.diff(ft) / 3600.0)
    dv = np.full(len(ft), np.nan); dv[1:] = np.where((dt_h > 0) & (dt_h <= 24), dt_h, np.nan)
    ivf = np.where(np.isfinite(fiv), fiv, dv); ivf = np.where(np.isfinite(ivf), ivf, 8.0)
    ivf = ALLOWED[np.argmin(np.abs(ivf[:, None] - ALLOWED[None, :]), axis=1)]
    rn = fr * (8.0 / ivf)
    pos = np.searchsorted(ft, anchor_s, side="right") - 1
    okp = pos >= 0
    for name, HL in HLs.items():
        e = np.full(len(ft), np.nan)
        acc = None; prev = None
        for k in range(len(ft)):
            if acc is None: acc = rn[k]
            else:
                a = 1 - 0.5 ** (max(ft[k] - prev, 1) / HL)
                acc = acc + a * (rn[k] - acc)
            prev = ft[k]; e[k] = acc
        out[name][okp, j] = e[pos[okp]].astype(np.float32)
    if j % 200 == 0: print("refold", j, flush=True)
for name in HLs: save(name, out[name])
print("FEMAT_BUILD_DONE", flush=True)
