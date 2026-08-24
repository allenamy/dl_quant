"""复审装置 @jpline。判据 REVIEW_f10_blend_deployment(SHA 25737433, commit 8e20be0)先于本数字。
阶段1: 全家族净额矩阵(45+ 配置逐锚 net_g2); 阶段2: PBO(CSCV S=12)/DSR/杠杆表/regime×事件表/成本压力。"""
import os, sys, json, time, hashlib, itertools, math
import numpy as np
HERE = "/mnt/storage/private/work_hsy/f8_2026-08-22"; sys.path.insert(0, HERE)
import f3_zoo_nonfunding_leg as f3
OUT = HERE; T0 = time.time()
def log(*a): print(f"[{time.time()-T0:7.1f}s]", *a, flush=True)
R3 = f3.load_all()
nE = f3.G["nE"]; NW = f3.G["NW"]; wa_ts = f3.G["E_ts"].copy(); wa_syms = f3.G["syms"]
import numpy as _np
DLW = "/mnt/storage/private/work_hsy/dlw_2026-08-22"
TG = np.load(f"{DLW}/data/dlw_targets.npz", allow_pickle=True)
dts = TG["E_ts"].astype(np.int64); dsyms = [str(s) for s in TG["symbols"]]
# 训练标签口径断言: y4s 与 f3 简单 RET 在共同 (锚,名) 上一致
y4s = TG["y4s"]; smap = np.array([wa_syms.index(s) if s in wa_syms else -1 for s in dsyms]); rmap = {int(t): j for j, t in enumerate(wa_ts)}
diffs = []
for i in range(0, len(dts), 977):
    j = rmap.get(int(dts[i]))
    if j is None: continue
    ok = smap >= 0
    a = y4s[i][ok]; b = f3.G["RET"][f3.G["ai_E"][j]][smap[ok]]
    m = np.isfinite(a) & np.isfinite(b)
    if m.sum() > 50: diffs.append(float(np.nanmedian(np.abs(a[m] - b[m]))))
assert diffs and np.median(diffs) < 1e-6, f"y4s≠简单RET: {np.median(diffs)}"
log("CALIBER_ASSERT_PASS y4s==simple RET, med|Δ|", np.median(diffs))
def align(p):
    P = np.load(p); M = np.full((nE, NW), np.nan, np.float32); ok = smap >= 0
    for i, t in enumerate(dts):
        j = rmap.get(int(t))
        if j is not None: M[j, ok] = P[i][ok]
    return M
PREDS = {}
for cfg in ("V2MAIN", "R1", "R1CTX", "RECB", "MAIN"):
    for sd in (42, 2027):
        p = f"{OUT}/preds/f10_{cfg}_s{sd}.npy"
        if os.path.exists(p): PREDS[f"F10.{cfg}.{sd}"] = align(p)
for nm, p in (("F4.K78", f"{OUT}/preds/f4_lgbm_K78raw.npy"), ("F4.K167", f"{OUT}/preds/f4_lgbm_K167raw.npy"),
              ("F6.b", f"{OUT}/preds/f6_lgbm_K78raw_ema.npy"), ("F6.c", f"{OUT}/preds/f6_lgbm_K167raw_ema.npy"),
              ("F6.e", f"{OUT}/preds/f6_lgbm_K78raw_ema_bn_a0.1.npy"), ("F6.d", f"{OUT}/preds/f6_lgbm_K167raw_ema_bn_a0.1.npy"),
              ("F8.ALL", f"{OUT}/preds/f8_lgbm_pALL.npy")):
    if os.path.exists(p): PREDS[nm] = align(p)
f3.G["ZC"] = {k: v for k, v in PREDS.items()}
log("preds aligned", len(PREDS))
# 链: C3r + 每配置换 king 槽
CH = {}; ACC = {}
def run(tag, legs):
    CH[tag] = f3.run_chain_n(legs, tag=tag); ACC[tag] = None
    idx = np.array([f3.G["apos"][int(t)] for t in CH[tag]["ts"]])
    ACC[tag] = f3.account(CH[tag]["W"], CH[tag]["ts"], {"fr_sum": f3.G["F"]["fr_sum"][idx]}, f3.G["RET"][idx], f3.G["LRET"][idx], cost_c=f3.COST_MAIN)
run("C3r", ("king", "rev24", "fund"))
for k in PREDS: run(k, (k, "rev24", "fund"))
base_ts = CH["C3r"]["ts"]; tp = {int(t): i for i, t in enumerate(base_ts)}
NETS = {"C3r": ACC["C3r"]["net_g2"]}
W_C3 = CH["C3r"]["W"]
BLENDS = {}
for k in list(PREDS):
    ts_f = CH[k]["ts"]; ib = np.array([tp.get(int(t), -1) for t in ts_f]); ok = ib >= 0
    NETS[k] = np.full(len(base_ts), np.nan); NETS[k][ib[ok]] = ACC[k]["net_g2"][ok]
    if k.startswith("F10."):
        for phi in (0.3, 0.45):
            Wb = (1 - phi) * W_C3[ib[ok]] + phi * CH[k]["W"][ok]
            idx = np.array([f3.G["apos"][int(t)] for t in ts_f[ok]])
            acc = f3.account(Wb, ts_f[ok], {"fr_sum": f3.G["F"]["fr_sum"][idx]}, f3.G["RET"][idx], f3.G["LRET"][idx], cost_c=f3.COST_MAIN)
            key = f"BL.{k[4:]}.{phi}"
            NETS[key] = np.full(len(base_ts), np.nan); NETS[key][ib[ok]] = acc["net_g2"]
            if phi == 0.45: BLENDS[key] = acc
log("family size", len(NETS))
np.savez(f"{OUT}/results/f10_review_nets.npz", ts=base_ts, **{k.replace(".", "_"): v for k, v in NETS.items()})
# ── PBO CSCV(S=12, 家族=全部配置+混合; 候选=BL.V2MAIN.{sd}.0.45) ──
common = np.ones(len(base_ts), bool)
for v in NETS.values(): common &= np.isfinite(v)
M = np.stack([NETS[k][common] for k in sorted(NETS)], 1); names = sorted(NETS)
S = 12; L = len(M) // S; M = M[:S * L].reshape(S, L, -1)
pbo_cnt = 0; tot = 0; cand_ranks = []
for tr in itertools.combinations(range(S), S // 2):
    te = [i for i in range(S) if i not in tr]
    mtr = M[list(tr)].reshape(-1, M.shape[-1]).mean(0); mte = M[te].reshape(-1, M.shape[-1]).mean(0)
    best = int(np.argmax(mtr)); r = (mte > mte[best]).mean()
    pbo_cnt += r > 0.5; tot += 1
    for cd in ("BL.V2MAIN.42.0.45", "BL.V2MAIN.2027.0.45"):
        if cd in names: cand_ranks.append(float((mte <= mte[names.index(cd)]).mean()))
PBO = pbo_cnt / tot
# ── DSR ──
def dsr(d):
    d = d[np.isfinite(d)]; n = len(d); sr = d.mean() / (d.std() + 1e-12)
    from scipy.stats import skew, kurtosis
    sk, ku = skew(d), kurtosis(d, fisher=False)
    NT = 50; e = 0.5772
    srmax = (1 - e) * (2 * math.log(NT)) ** 0.5 + e * (2 * math.log(NT * math.e)) ** 0.5
    sr0 = srmax * d.std() / max(n, 1) ** 0.5 / (d.std() + 1e-12) * (d.std())
    sr0 = srmax / max(n, 1) ** 0.5
    from scipy.stats import norm
    z = ((sr - sr0) * math.sqrt(n - 1)) / math.sqrt(max(1 - sk * sr + (ku - 1) / 4 * sr * sr, 1e-9))
    return float(norm.cdf(z))
rep = {"prereg_sha": "25737433", "caliber_assert": "PASS", "family_n": len(NETS), "PBO_S12": round(PBO, 3),
       "cand_mean_oos_percentile": round(float(np.mean(cand_ranks)), 3) if cand_ranks else None, "DSR": {}, "lev": {}, "regime": {}, "events": {}, "cost_stress": {}}
for cd in ("BL.V2MAIN.42.0.45", "BL.V2MAIN.2027.0.45"):
    d = NETS[cd][common] - NETS["C3r"][common]
    rep["DSR"][cd] = round(dsr(d), 3)
# ── 杠杆表(恒 gross)+ 区间 + regime + 事件 + 成本压力(对 s2027 主候选与 C3r)──
from scipy.stats import norm
mkt = np.array([f3.G["mkt"][np.searchsorted(f3.G["E_ts"], t)] for t in base_ts])
for cd in ("C3r", "BL.V2MAIN.2027.0.45", "BL.V2MAIN.42.0.45"):
    v = NETS[cd]; okv = np.isfinite(v); x = v[okv]
    ann = x.mean() * 2190 / 1e4
    for lev in (1.5, 2.0, 2.5, 3.0):
        y = x * lev / 2.0
        cum = np.cumsum(y) / 1e4; dd = np.maximum.accumulate(cum) - cum
        rng = np.random.default_rng(11); hit = 0
        blk = 42; nb = len(y) // blk
        for _ in range(300):
            ii = rng.integers(0, nb, 2190 // blk)
            yy = np.concatenate([y[j * blk:(j + 1) * blk] for j in ii])
            c2 = np.cumsum(yy) / 1e4
            hit += float(np.max(np.maximum.accumulate(c2) - c2) >= 0.25)
        rep["lev"].setdefault(cd, {})[str(lev)] = {"ann": round(float(ann * lev / 2), 4), "sharpe": round(float(x.mean() / x.std() * math.sqrt(2190)), 2),
                                                   "maxDD": round(float(dd.max()), 4), "p_hit25_yr": round(hit / 300, 3),
                                                   "es5_bps": round(float(-np.sort(y)[:max(1, len(y) // 20)].mean()), 2)}
    q = np.nanquantile(mkt[okv], [0.2, 0.4, 0.6, 0.8]); gb = np.digitize(mkt[okv], q)
    rep["regime"][cd] = [round(float(x[gb == g].mean()), 3) for g in range(5)]
    crash = mkt[okv] <= -0.03
    nx = np.where(crash[:-1])[0] + 1
    rep["events"][cd] = {"crash_anchor_net": round(float(x[crash].mean()), 3) if crash.any() else None,
                         "post_crash_next": round(float(x[nx].mean()), 3) if len(nx) else None, "n_crash": int(crash.sum())}
for cc in (3.52, 6.64, 10.0):
    d45 = BLENDS.get("BL.V2MAIN.2027.0.45")
    if d45 is not None:
        key = f"net_g2_c{cc}" if cc != 3.52 else "net_g2"
        arr = d45.get(key) if cc != 3.52 else d45["net_g2"]
        if arr is None and f"net_g2_c{cc}" in d45: arr = d45[f"net_g2_c{cc}"]
        if arr is not None:
            rep["cost_stress"][str(cc)] = {"net": round(float(np.nanmean(arr)), 3), "sharpe": round(float(np.nanmean(arr) / (np.nanstd(arr) + 1e-12) * math.sqrt(2190)), 2)}
json.dump(rep, open(f"{OUT}/results/f10_review.json", "w"), indent=1, default=float)
log("REVIEW_DONE", json.dumps({k: rep[k] for k in ("PBO_S12", "cand_mean_oos_percentile", "DSR")}, ensure_ascii=False))
