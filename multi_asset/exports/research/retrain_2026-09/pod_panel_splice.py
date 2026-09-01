"""面板拼接 v3splice @pod(2026-09-01 守卫红归因后的修复):
≤cut(正典末锚): 全 18 列逐字 = v1 正典; >cut: kline 13 列 + fund_now/f_fund_iv = ext(重叠 parity 1.0/0.9999 zip 真值),
ema_v0/v1/v2 = 以正典 cut 行值为状态种子, 只折 cut 后事件(zip+AUG, 与 pod_panel_ext.py 同解析同更新规则)续算。
受据: 干预实验(guard_recon_v1panel) — 正典面板守卫 2.49 带内, 我的全史重算 ema_v1 秩放大掉 0.4 夏普。
产物: wide_panel_4h_v3splice.npz + fund_state_canoncont.json(每名 {acc(v1), last_ts}, 供 bundle §3 种子)。
断言: cut 行三 EMA 列 == 正典逐位; >cut 行 kline 列 == ext 逐位。
"""
import os, io, csv, json, glob, gzip, zipfile
import numpy as np

CAN = np.load("/workspace/data/wide_panel_4h_v1.npz", allow_pickle=True)
EXT = np.load("/workspace/data/wide_panel_4h_v2ext.npz", allow_pickle=True)
syms = [str(s) for s in CAN["symbols"]]
assert syms == [str(s) for s in EXT["symbols"]]
ct = CAN["ts"].astype(np.int64); et = EXT["ts"].astype(np.int64)
cut = int(ct[-1])
tail_idx = np.where(et > cut)[0]
keys = sorted(set(CAN.files) & set(EXT.files) - {"ts", "symbols"})
print(f"cut {cut} 正典锚 {len(ct)} ext尾锚 {len(tail_idx)} 拼接列 {len(keys)}", flush=True)

out = {"ts": np.concatenate([ct, et[tail_idx]]), "symbols": np.array(syms)}
for k in keys:
    a = CAN[k]; b = EXT[k]
    if a.ndim == 2 and a.shape[1] == len(syms):
        out[k] = np.concatenate([a, b[tail_idx]])
    else:
        out[k] = a  # 非锚×名列(elig等): 正典段为准, 尾部另行处理仅当被消费(guard/export 只用 f_* 与 ts)

# ---- EMA 族尾部续算(种子 = 正典 cut 行) ----
HL = 3 * 86400.0
ALLOWED = np.array([1.0, 2.0, 4.0, 6.0, 8.0])
AUG = json.loads(gzip.open("/workspace/fund_aug.json.gz", "rt").read())
AUG_IV = {k2: float(v) for k2, v in (AUG.get("intervals") or {}).items() if v}
fdir = "/workspace/wide_multisrc/funding"
tail_ts = et[tail_idx]
row_of = {int(t): r for r, t in enumerate(tail_ts)}
nC = len(ct)
state = {}
n_cont = 0
for j, s in enumerate(syms):
    rows = []
    for zp in sorted(glob.glob(f"{fdir}/{s}/*.zip")):
        try:
            zf = zipfile.ZipFile(zp)
            with zf.open(zf.namelist()[0]) as fh:
                rd = csv.reader(io.TextIOWrapper(fh))
                for row in rd:
                    if not row or not row[0].strip().isdigit() and "time" in row[0].lower(): continue
                    try:
                        ts_ = int(row[0]); rate = float(row[-1]) if abs(float(row[-1])) < 0.2 else float(row[1])
                        iv = np.nan
                        if len(row) >= 3:
                            try:
                                cand = float(row[1])
                                if 1 <= cand <= 24 and abs(cand - round(cand)) < 1e-9 and abs(float(row[-1])) < 0.2: iv = cand
                            except Exception: pass
                        rows.append((ts_ // 1000, rate, iv))
                    except Exception: continue
        except Exception: continue
    for t_ms, rate in (AUG.get("rates") or {}).get(s, []):
        rows.append((int(t_ms) // 1000, float(rate), AUG_IV.get(s, np.nan)))
    if not rows: continue
    rows.sort()
    ded = {}
    for t_, r_, i_ in rows:
        if t_ not in ded or np.isfinite(i_): ded[t_] = (r_, i_)
    ft = np.array(sorted(ded), np.int64)
    fr = np.array([ded[t][0] for t in ft]); fiv = np.array([ded[t][1] for t in ft])
    dt_h = np.round(np.diff(ft) / 3600.0)
    dv = np.full(len(ft), np.nan); dv[1:] = np.where((dt_h > 0) & (dt_h <= 24), dt_h, np.nan)
    iv_full = np.where(np.isfinite(fiv), fiv, dv)
    iv_full = np.where(np.isfinite(iv_full), iv_full, 8.0)
    iv_full = ALLOWED[np.argmin(np.abs(iv_full[:, None] - ALLOWED[None, :]), axis=1)]
    rate_nf = fr * (8.0 / iv_full)
    # 种子: 正典 cut 行(缺=NaN ⇒ 无正典史, 回退 ext 值不续算)
    seeds = {}
    for name, col in (("v0", "f_fund_ema"), ("v1", "f_fund_ema_v1"), ("v2", "f_fund_ema_v2")):
        seeds[name] = float(CAN[col][-1, j]) if np.isfinite(CAN[col][-1, j]) else None
    if seeds["v1"] is None:
        continue  # 尾部保持 ext 原值(新上市名, 无正典口径可续)
    n_cont += 1
    sel = ft > cut
    e0, e1 = seeds["v0"], seeds["v1"]; e2 = seeds["v2"]
    prev_t = cut
    # v2 span: 结算空间 adjust=False span=max(2,round(24/iv中位))
    ivm = np.median(iv_full[sel]) if sel.any() else 8.0
    span = max(2, round(24 / ivm)); al2 = 2.0 / (span + 1.0)
    ptr = np.where(sel)[0]
    k2 = 0
    for r_row, t_anchor in enumerate(tail_ts):
        while k2 < len(ptr) and ft[ptr[k2]] <= t_anchor:
            i_ = ptr[k2]
            a = 1 - 0.5 ** (max(ft[i_] - prev_t, 1) / HL)
            e0 = e0 + a * (fr[i_] - e0)
            e1 = e1 + a * (rate_nf[i_] - e1)
            e2 = e2 + al2 * (rate_nf[i_] - e2) if e2 is not None else rate_nf[i_]
            prev_t = ft[i_]
            k2 += 1
        r = nC + r_row
        out["f_fund_ema"][r, j] = np.float32(e0)
        out["f_fund_ema_v1"][r, j] = np.float32(e1)
        if e2 is not None: out["f_fund_ema_v2"][r, j] = np.float32(e2)
    state[s] = {"acc": float(e1), "last_ts": int(prev_t)}

# ---- 断言 ----
r_cut = nC - 1
for col in ("f_fund_ema", "f_fund_ema_v1", "f_fund_ema_v2"):
    va = CAN[col][-1]; vb = out[col][r_cut]
    ok = np.isfinite(va)
    assert np.array_equal(va[ok], vb[ok]), f"cut 行 {col} 不等"
for col in ("f_rev_24h", "f_mom_7d", "f_vol_7d"):
    va = EXT[col][tail_idx]; vb = out[col][nC:]
    ok = np.isfinite(va)
    assert np.array_equal(va[ok], vb[ok]), f"尾部 {col} != ext"
json.dump(state, open("/workspace/fund_state_canoncont.json", "w"), indent=0)
np.savez_compressed("/workspace/data/wide_panel_4h_v3splice.npz", **out)
print(f"SPLICE_DONE anchors {len(out['ts'])} 续算名 {n_cont} state名 {len(state)}", flush=True)
