"""★ 修正后的尺子: 秩位加权 / 尾部 IC —— 取代 E75 被自己证伪的 ORD/SIZE 分解。

E75 教到的准确盲区: **不是"幅度", 是"改善发生在秩分布的哪个位置"。**
rank-IC 对秩位【等权】(第1↔2 名对调与第50↔51 名对调同分), 而 P&L 按【仓位】加权。
⇒ 排序改善若集中在两端的大仓位上, 能大幅改 P&L 而几乎不动 rank-IC。

三个口径并排:
  IC_full  = 现有全横截面 Spearman(书权重 vs 收益)
  IC_wtd   = 以 |w_i| 为权的加权 Pearson-on-ranks(直接对齐 P&L 的加权方式)
  IC_tail  = 只在 |w| 的上下各 20% 名字上算的 Spearman(书真正下注的地方)

★ 会红的验证(先写死): C1 的 dIC_full 实测 ≈ 0(+0.00008, CI 跨零)却带来 +0.053 毛额。
   若本尺子是对的, **C1 的 dIC_tail / dIC_wtd 应明显非零**。
   若三个口径都是零 ⇒ 增益不走排序通道, 本尺子作废、E75 的"ORD 占 87%"也须重新解释。
"""
import sys, json, time, numpy as np, pandas as pd
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset")
exec(open("/mnt/storage/private/work_hsy/probe_artifacts/breadth2.py").read().split('R = {"prereg_sha"')[0])

TAIL_Q = 0.20
WPROBE = [0.05, 0.10]
OUT = "/mnt/storage/private/work_hsy/probe_artifacts/tail_ic_gate.json"


def ics(w, r):
    """返回 (IC_full, IC_wtd, IC_tail)。w = 书权重(已 demean, 单位 gross), r = 实现收益。"""
    ok = np.isfinite(w) & np.isfinite(r)
    if ok.sum() < 10:
        return np.nan, np.nan, np.nan
    w_, r_ = w[ok], r[ok]
    rw = pd.Series(w_).rank().values; rr = pd.Series(r_).rank().values
    ic_full = float(np.corrcoef(rw, rr)[0, 1])
    om = np.abs(w_)
    if om.sum() <= 1e-12:
        return ic_full, np.nan, np.nan
    p = om / om.sum()
    mw = (p*rw).sum(); mr = (p*rr).sum()
    cov = (p*(rw-mw)*(rr-mr)).sum()
    sw = np.sqrt((p*(rw-mw)**2).sum()); sr = np.sqrt((p*(rr-mr)**2).sum())
    ic_wtd = float(cov/(sw*sr)) if sw > 1e-12 and sr > 1e-12 else np.nan
    k = max(int(round(TAIL_Q*len(w_))), 3)
    idx = np.argsort(w_)
    sel = np.concatenate([idx[:k], idx[-k:]])
    ic_tail = float(np.corrcoef(pd.Series(w_[sel]).rank().values,
                                pd.Series(r_[sel]).rank().values)[0, 1]) if len(sel) >= 6 else np.nan
    return ic_full, ic_wtd, ic_tail


def book_ics(cand, variant, w_c):
    base_w = np.array([LIVE3["king"], LIVE3["s2"], LIVE3["funding"]]) * (1.0 - w_c)
    out = np.full((len(anchors), 3), np.nan)
    for i in range(len(anchors)):
        m = M[i]
        combo = base_w @ HELD[i]
        if cand:
            combo = combo + w_c * CAND[cand][variant][i]
        shaped = rb(chain.shape_position(combo[m]), RVOL[i])
        g = float(np.abs(shaped).sum())
        if g > 1e-12:
            shaped = shaped / g
        out[i] = ics(shaped, RET[i])
    return out


def boot(d, nb=3000, bl=5):
    d = d[np.isfinite(d)]
    rng = np.random.default_rng(31337); n = len(d); nb_ = int(np.ceil(n/bl)); o = np.empty(nb)
    for k in range(nb):
        st = rng.integers(0, max(n-bl, 1), size=nb_)
        idx = (st[:, None]+np.arange(bl)[None, :]).ravel()[:n]; idx = idx[idx < n]
        o[k] = np.nanmean(d[idx])
    return float(np.percentile(o, 2.5)), float(np.percentile(o, 97.5))


t0 = time.time()
B = book_ics(None, "real", 0.0)
NAMES = ["IC_full", "IC_wtd", "IC_tail"]
print(f"基线书: " + "  ".join(f"{n}={np.nanmean(B[:, j]):+.5f}" for j, n in enumerate(NAMES)), flush=True)
R = {"tail_q": TAIL_Q, "baseline": {n: round(float(np.nanmean(B[:, j])), 5) for j, n in enumerate(NAMES)}, "arms": {}}
print("\n臂         w      " + "".join(f"{n:>28s}" for n in NAMES))
print("-"*98)
for cand in ["C1", "C2"]:
    for wc in WPROBE:
        A = book_ics(cand, "real", wc)
        row = {}
        cells = []
        for j, n in enumerate(NAMES):
            d = A[:, j] - B[:, j]
            mu = float(np.nanmean(d)); lo, hi = boot(d)
            row[n] = {"d": round(mu, 6), "CI": [round(lo, 6), round(hi, 6)]}
            cells.append(f"{mu:+.5f}[{lo:+.5f},{hi:+.5f}]")
        R["arms"][f"{cand}_w{wc}"] = row
        print(f"{cand:4s} {wc:.2f}  " + "".join(f"{c:>28s}" for c in cells), flush=True)

print("\n===== ★ 会红的验证 (C1: dIC_full 实测 ≈ 0 却带来 +0.053 毛额) =====")
c1 = R["arms"]["C1_w0.1"]
zero_full = abs(c1["IC_full"]["d"]) < 2e-4
nz_tail = c1["IC_tail"]["CI"][0] > 0 or c1["IC_tail"]["CI"][1] < 0
nz_wtd = c1["IC_wtd"]["CI"][0] > 0 or c1["IC_wtd"]["CI"][1] < 0
print(f"  IC_full ≈0 ? {zero_full}  (d={c1['IC_full']['d']:+.6f})")
print(f"  IC_tail 非零? {nz_tail}   (d={c1['IC_tail']['d']:+.6f} CI{c1['IC_tail']['CI']})")
print(f"  IC_wtd  非零? {nz_wtd}    (d={c1['IC_wtd']['d']:+.6f} CI{c1['IC_wtd']['CI']})")
ok = zero_full and (nz_tail or nz_wtd)
print(f"  ⇒ 尺子{'成立' if ok else '【不成立】—— 三口径皆零则本尺作废, E75 的 ORD 解释也须重述'}")
R["validation"] = {"IC_full_is_zero": bool(zero_full), "IC_tail_nonzero": bool(nz_tail),
                   "IC_wtd_nonzero": bool(nz_wtd), "instrument_valid": bool(ok)}
json.dump(R, open(OUT, "w"), indent=1)
print(f"\n[done] {time.time()-t0:.0f}s -> {OUT}\nTAILIC_DONE")
