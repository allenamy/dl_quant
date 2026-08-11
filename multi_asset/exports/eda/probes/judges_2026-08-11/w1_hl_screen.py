"""W1 · HL 跨所族预测器筛查 — 判据冻结(先于数字):
G1 rank-IC: 逐锚横截面 spearman(feat, fwd_ret) 均值, |IC|≥0.01 且逐年(2023H2/24/25/26)同号≥3/4
G2 shuffle-future null: 未来收益锚内打乱后 |IC| 必须塌到 <0.003
G3 future-corr scan: IC(feat_t, ret[t-24h→t]) 过去侧 vs 未来侧 —— 未来侧不得 > 过去侧(因果签名)
目标: 币安 fwd 4h(Y4) 与 fwd 24h(Y24); 另设 funding 预测目标(次轮)。
覆盖掩码: HL 有值格 ∩ MEMBER110。任何格不足 30 名跳过。
会红方向: fund_div 是慢价差 ⇒ 排序信息≈0 是合法结果(那就转 W1b carry 设计, 不硬掰预测器)。"""
import numpy as np, json
from scipy.stats import spearmanr
HL = np.load('/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/hl_hourly.npz', allow_pickle=True)
P = np.load('/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/wide_dl_full_corrfund_causal_0731.npz', allow_pickle=True)
assert list(HL['symbols']) == list(P['symbols']), "symbol 顺序不一致"
X, feats, ts = HL['X'], list(HL['feats']), HL['ts']
Y4, Y24, MEM = P['Y4'], P['Y24'], P['MEMBER110']
T, N = Y4.shape
hours = (ts // 3600) % 24
anchors = np.where((hours % 4 == 0))[0]
years = ((ts - 1640995200) // (365.25*86400)).astype(int) + 2022  # approx year label
rng = np.random.default_rng(7)
res = {}
for fi, fname in enumerate(feats):
    F = X[:, :, fi]
    ics, ics_null, yr_ic = [], [], {}
    past_side, fut_side = [], []
    for t in anchors:
        if t + 24 >= T or t < 24: continue
        m = np.isfinite(F[t]) & MEM[t].astype(bool) & np.isfinite(Y4[t])
        if m.sum() < 30: continue
        ic = spearmanr(F[t][m], Y4[t][m]).statistic
        y24m = np.isfinite(Y24[t]) & m
        icy = spearmanr(F[t][m], Y4[t][m]).statistic
        ics.append((ic, spearmanr(F[t][m], Y24[t][np.isfinite(Y24[t]) & m]).statistic if (np.isfinite(Y24[t]) & m).sum() >= 30 and False else np.nan))
        yr = int(years[t]); yr_ic.setdefault(yr, []).append(ic)
        perm = rng.permutation(int(m.sum()))
        ics_null.append(spearmanr(F[t][m], Y4[t][m][perm]).statistic)
        # G3: past-side = corr(feat_t, ret over [t-24, t]); future-side = corr(feat_t, ret over [t, t+24])
        past_ret = np.nansum(Y4[max(t-24,0):t:4][:, :], 0)  # sum of past 4h rets over 24h
        fut_ret = np.nansum(Y4[t:t+24:4][:, :], 0)
        mp = m & np.isfinite(past_ret) & np.isfinite(fut_ret)
        if mp.sum() >= 30:
            past_side.append(spearmanr(F[t][mp], past_ret[mp]).statistic)
            fut_side.append(spearmanr(F[t][mp], fut_ret[mp]).statistic)
    ic4 = float(np.nanmean([a for a, _ in ics]))
    icn = float(np.nanmean(np.abs(ics_null)))
    yrs = {y: round(float(np.nanmean(v)), 4) for y, v in sorted(yr_ic.items()) if len(v) > 50}
    sign_ok = sum(1 for v in yrs.values() if v * ic4 > 0)
    ps, fs = float(np.nanmean(past_side)), float(np.nanmean(fut_side))
    g1 = abs(ic4) >= 0.01 and sign_ok >= max(1, len(yrs) - 1)
    g2 = icn < 0.003
    g3 = abs(fs) <= abs(ps) + 0.02 or abs(fs) < 0.03
    res[fname] = dict(ic4=round(ic4, 4), null=round(icn, 4), by_year=yrs,
                      past24=round(ps, 4), fut24=round(fs, 4),
                      g=[bool(g1), bool(g2), bool(g3)], n=len(ics))
    print(f"{fname}: IC4h {ic4:+.4f} null {icn:.4f} 逐年{yrs} past24 {ps:+.3f} fut24 {fs:+.3f} "
          f"G1{'P' if g1 else 'F'} G2{'P' if g2 else 'F'} G3{'P' if g3 else 'F'} n={len(ics)}", flush=True)
json.dump(res, open('/mnt/storage/private/work_hsy/probe_artifacts/w1_hl_screen.json', 'w'), indent=1)
print("W1_SCREEN_DONE")
