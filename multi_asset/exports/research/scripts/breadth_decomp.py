"""PROPOSAL 00 §3 的测量 —— 逐字执行, 判读规则已封于 §4, 本脚本不解释结果。

N_eff = (Σλ)² / Σλ²   参与率(1 = 全同向; N = 全独立)
(a) 宇宙: 逐时间戳 xsec-demean 的 Y4, 名字间相关阵的参与率
(b) 书:   同一相关阵 + 书的实际权重, 风险沿主成分分布的参与率
"""
import sys, json
import numpy as np
MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
PANEL = f"{MA}/exports/wide_dl_full_corrfund_causal_0731.npz"
from scipy.stats import rankdata


def neff_from_corr(C):
    """参与率。相关阵的 trace = N, 故 N_eff = N² / Σλ²。"""
    lam = np.linalg.eigvalsh(C)
    lam = np.clip(lam, 0, None)
    s = lam.sum()
    return float(s * s / np.square(lam).sum()) if s > 0 else float("nan")


def corr_of(R):
    """R: (T, N) 已 xsec-demean 的收益。列间相关, 要求足够重叠。

    ★ 先滤【行】再滤【列】: CL4 是整行的 stride 掩码(实测 19.6% 的行带满 110 名, 其余整行为空)。
    在全部行上算列覆盖率 ⇒ 没有一列过 0.8 ⇒ 静默返回空表。先扔掉空行, 覆盖率才有意义。"""
    R = R[np.isfinite(R).sum(1) >= 20]
    if R.shape[0] < 50:
        return None, 0, 0, None
    ok = np.isfinite(R).mean(0) > 0.8
    R = R[:, ok]
    R = R[np.isfinite(R).all(1)]
    if R.shape[0] < 50 or R.shape[1] < 5:
        return None, 0, 0, None
    C = np.corrcoef(R, rowvar=False)
    C = np.nan_to_num(C, nan=0.0)
    np.fill_diagonal(C, 1.0)
    return C, R.shape[0], R.shape[1], R


# ══ 有效性检查: 装置必须能分辨已知答案 (§3) ══
rng = np.random.default_rng(20260806)
out = {"validity": {}, "partner": {}, "universe": {}, "book": {}}
_iid = rng.normal(size=(4000, 110))
C_iid, _, n_iid, _ = corr_of(_iid)
out["validity"]["iid_110"] = round(neff_from_corr(C_iid), 1)
_f = rng.normal(size=(4000, 1))
_one = _f @ np.ones((1, 110)) + 0.01 * rng.normal(size=(4000, 110))
C_one, _, _, _ = corr_of(_one)
out["validity"]["one_factor"] = round(neff_from_corr(C_one), 2)
_ok = (abs(out["validity"]["iid_110"] - 110) < 12) and (out["validity"]["one_factor"] < 1.5)
out["validity"]["PASS"] = bool(_ok)
print(f"[有效性] iid110 -> N_eff={out['validity']['iid_110']} (须≈110); "
      f"单因子 -> {out['validity']['one_factor']} (须≈1)  ⇒ {'PASS' if _ok else '★FAIL 全表作废'}",
      flush=True)
if not _ok:
    sys.exit(1)

z = np.load(PANEL, allow_pickle=True)
ts = z["ts"].astype(np.int64)
Y4 = z["Y4"].astype(np.float64)
CL4 = z["CL4"].astype(bool)
MEM = z["MEMBER110"].astype(bool)
ch = [str(x) for x in z["ch_names"]]
CH = z["CH"]
import datetime as dt
ts_s = ts // 1000 if int(ts[0]) > 10**11 else ts
years = np.array([dt.datetime.utcfromtimestamp(int(t)).year for t in ts_s])

# 只用干净非重叠格 & member; xsec demean = 市场中性书的真实暴露
Rm = np.where(MEM & CL4, Y4, np.nan)
mu = np.nanmean(Rm, axis=1, keepdims=True)
Rd = Rm - mu

print("\n[(a) 宇宙提供多少 —— 逐年, 附【同形状噪声地板】]", flush=True)
_keep = {}
for yr in (2022, 2023, 2024, 2025, 2026):
    sel = years == yr
    C, T, N, Rf = corr_of(Rd[sel])
    if C is None:
        continue
    ne = neff_from_corr(C)
    off = C[np.triu_indices_from(C, 1)]
    # ★ 同形状噪声地板: 纯随机 (T,N) 的 N_eff。没有它, "N_eff=46" 无法与"估计噪声撑起来的"区分。
    Cn, _, _, _ = corr_of(rng.normal(size=(T, N)))
    ne_null = neff_from_corr(Cn)
    _keep[yr] = (C, Rf, N, T)
    out["universe"][str(yr)] = {"n_eff": round(ne, 2), "n_eff_noise_floor": round(ne_null, 2),
                               "n_names": N, "n_ts": T,
                               "mean_offdiag_corr": round(float(np.mean(off)), 4),
                               "top1_var_share": round(float(np.sort(np.linalg.eigvalsh(C))[-1] / N), 4)}
    print(f"  {yr}: N={N:3d} T={T:5d}  N_eff={ne:6.2f}  (同形状噪声地板 {ne_null:5.1f})  "
          f"平均非对角={np.mean(off):+.3f}  PC1={np.sort(np.linalg.eigvalsh(C))[-1]/N:.1%}", flush=True)

# ══ 伙伴检查: 读数不能是装置造的 (§3) ══
C24, Rf24, N24, T24 = _keep[2024]
perm = rng.permutation(N24)
out["partner"]["name_shuffle_invariant"] = round(neff_from_corr(C24[np.ix_(perm, perm)]), 2)
Rt = Rf24.copy()
for j in range(Rt.shape[1]):
    Rt[:, j] = Rt[rng.permutation(Rt.shape[0]), j]
Ct, _, _, _ = corr_of(Rt)
out["partner"]["time_shuffle_rises_to"] = round(neff_from_corr(Ct), 2)
out["partner"]["baseline_2024"] = round(neff_from_corr(C24), 2)
print(f"\n[伙伴检查] 2024 基线 {out['partner']['baseline_2024']} | 名字打乱 "
      f"{out['partner']['name_shuffle_invariant']}(须逐位不变) | 时间打乱 "
      f"{out['partner']['time_shuffle_rises_to']}(须升向噪声地板)", flush=True)

# ══ (b) 书实际收割多少 ══
def rank_c(x):
    o = np.zeros_like(x, dtype=np.float64)
    m = np.isfinite(x)
    if m.sum() < 3:
        return o
    r = rankdata(x[m]); k = len(r)
    o[m] = 2.0 * (r - 1) / (k - 1) - 1.0
    return o


def l1(x):
    s = np.abs(x).sum()
    return x / s if s > 0 else x


K = np.load("/tmp/king_pred_newgen.npz", allow_pickle=True)
S = np.load("/tmp/s2_pred_newgen.npz", allow_pickle=True)
kpos = {int(t): i for i, t in enumerate(K["ts"])}
spos = {int(t): i for i, t in enumerate(S["ts"])}
kp, sp = K["king_pred"], S[[f for f in S.files if f != "ts"][0]]
rv_i = ch.index("rvol_24h")
W = {"king": .5952380952380952, "s2": .20238095238095238}

print("\n[(b) 书实际收割多少 —— 逐年, 线上配方 rank→L1→cap99→demean→σ缩放]", flush=True)
for yr in (2022, 2023, 2024, 2025, 2026):
    if yr not in _keep:
        continue
    sel = np.where((years == yr))[0]
    C, _Rf, _N, _T = _keep[yr]
    _rows = Rd[years == yr]
    _rows = _rows[np.isfinite(_rows).sum(1) >= 20]
    okn = np.isfinite(_rows).mean(0) > 0.8
    lam, V = np.linalg.eigh(C)
    lam = np.clip(lam, 0, None)
    nbs, nbs_eq = [], []
    for i in sel[::13]:                      # 每 13 个锚采一个, 够统计且快
        t = int(ts[i])
        if t not in kpos or t not in spos:
            continue
        m = MEM[i] & okn
        if m.sum() < 20:
            continue
        sc = W["king"] * l1(rank_c(np.where(m, kp[kpos[t]], np.nan))) \
            + W["s2"] * l1(rank_c(np.where(m, sp[spos[t]], np.nan)))
        lo, hi = np.nanpercentile(sc[m], [0.5, 99.5])
        sc = np.clip(sc, lo, hi)
        sc = sc - sc[m].mean()
        sig = CH[i, :, rv_i].astype(np.float64)
        fin = np.isfinite(sig) & (sig > 0) & m
        if fin.sum() > 5:
            med = np.median(sig[fin])
            sig = np.where(fin, sig, med)
            sc = np.sign(sc) * np.abs(sc) ** 0.5 / np.power(sig / med, 1.0)   # α=.5 λ=1
            sc = sc - sc[m].mean()
        w = l1(np.where(m, sc, 0.0))[okn]
        if not np.isfinite(w).all() or np.abs(w).sum() == 0:
            continue
        r = np.square(V.T @ w) * lam                # 沿主成分的风险贡献
        if r.sum() > 0:
            nbs.append(r.sum() ** 2 / np.square(r).sum())
        we = l1(np.sign(rng.normal(size=w.shape)))  # 参照: 等额随机符号书
        re = np.square(V.T @ we) * lam
        nbs_eq.append(re.sum() ** 2 / np.square(re).sum())
    if nbs:
        out["book"][str(yr)] = {"n_eff_book": round(float(np.mean(nbs)), 2),
                                "n_eff_equalweight_ref": round(float(np.mean(nbs_eq)), 2),
                                "n_anchors": len(nbs)}
        print(f"  {yr}: N_eff^book={np.mean(nbs):5.2f}   (等额随机符号参照 {np.mean(nbs_eq):5.2f}, "
              f"宇宙 {out['universe'].get(str(yr), {}).get('n_eff')})  n={len(nbs)}", flush=True)

json.dump(out, open(f"{MA}/exports/eda/RESULT_breadth_decomp_2026-08-06.json", "w"), indent=1)
u = [v["n_eff"] for v in out["universe"].values()]
b = [v["n_eff_book"] for v in out["book"].values()]
print(f"\n★ 汇总: N_eff^universe 均值 {np.mean(u):.2f} | N_eff^book 均值 "
      f"{np.mean(b) if b else float('nan'):.2f} | 比值 {np.mean(u)/np.mean(b) if b else float('nan'):.2f}×",
      flush=True)
