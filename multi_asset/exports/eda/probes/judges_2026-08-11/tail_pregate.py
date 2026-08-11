"""IR 顶部加权列表损失(NDCG@k 族)候选的决定性前置门 · 判据冻结(先于数字)
机制: 顶部加权损失把训练精度从中段挪到尾段。立项当且仅当两条同时成立:
 (a) 有差距可挪 —— 尾段(顶/底各1/3)段内 spearman < 中段 −0.01, 且逐年同向 ≥4/5;
 (b) 挪过去有回报 —— 钱集中在极端档: 边缘贡献占比 (D10−D9)+(D2−D1) 份额 ≥ 0.40 × (D10−D1)。
任一不成立 ⇒ 候选关闭(损失族最后一个带机制的候选)。对 king 分数与复合新鲜目标双测, king 为主判(损失训的是它)。"""
import sys
MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0, MA); sys.path.insert(0, MA + "/engine/live")
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")
PD = "/mnt/storage/private/work_hsy/probe_artifacts"; sys.path.insert(0, PD)
import numpy as np, pandas as pd
from scipy.stats import spearmanr
import legs as LG
import engine.replay_fullhist as RF
W = {"king": .5952380952380952, "s2": .20238095238095238, "funding": .20238095238095238, "size": 0.}
RB = {"alpha": .5, "lambda": 1.}
src = RF.get_src(None, f"{PD}/king_pred_newgen.npz", f"{PD}/s2_pred_newgen.npz")
a, yr = RF._all_anchors(src); N = src.N
FI, RVI = src.fund_idx, src.ch.index("rvol_24h")
def spear(x, y):
    ok = np.isfinite(x) & np.isfinite(y)
    return spearmanr(x[ok], y[ok]).correlation if ok.sum() >= 8 else np.nan
res = {"king": {"top": [], "mid": [], "bot": []}, "comp": {"top": [], "mid": [], "bot": []}}
dec_prof = []
held = {"k": np.full(N, np.nan), "s": np.full(N, np.nan), "f": np.full(N, np.nan)}
yrs_used = []
for i, t in enumerate(a):
    ti = int(t); m = np.asarray(src.tradeable(ti))
    if m.dtype == bool: m = np.where(m)[0]
    if i == 0 or ti % 8 == 0:
        v = np.full(N, np.nan); v[m] = src.king[ti, m]; held["k"] = v
    if i == 0 or ti % 24 == 0:
        v = np.full(N, np.nan); v[m] = src.s2[ti, m]; held["s"] = v
    if i == 0 or ti % 8 == 0:
        v = np.full(N, np.nan); v[m] = src.CH[ti, m, FI]; held["f"] = v
    rv = src.CH[ti, m, RVI].astype(float)
    r = LG.compose_book(held["k"][m], held["s"][m], held["f"][m], np.ones(len(m)),
                        weights=W, rvol=rv, risk_budget=RB)
    comp = np.asarray(r["target_w"], float)
    y = src.Y4[ti, m].astype(float)
    for nm, s in (("king", held["k"][m]), ("comp", comp)):
        ok = np.isfinite(s) & np.isfinite(y)
        if ok.sum() < 30: continue
        ss, yy = s[ok], y[ok]
        q = np.argsort(np.argsort(ss)) / (ok.sum() - 1)
        for seg, msk in (("bot", q <= 1/3), ("mid", (q > 1/3) & (q < 2/3)), ("top", q >= 2/3)):
            res[nm][seg].append(spear(ss[msk], yy[msk]))
    okk = np.isfinite(held["k"][m]) & np.isfinite(y)
    if okk.sum() >= 50:
        ss, yy = held["k"][m][okk], y[okk]
        edges = np.quantile(ss, np.linspace(0, 1, 11))
        d = np.clip(np.searchsorted(edges, ss, side="right") - 1, 0, 9)
        prof = [np.nanmean(yy[d == k]) - np.nanmean(yy) for k in range(10)]
        dec_prof.append(prof); yrs_used.append(yr[i])
print("== (a) 段内排序质量(9821 锚均值) ==")
verdict_a = {}
for nm in ("king", "comp"):
    tm = {seg: np.nanmean(res[nm][seg]) for seg in ("bot", "mid", "top")}
    dfy = pd.DataFrame({"y": yr[:len(res[nm]["top"])],
                        "gap_t": np.array(res[nm]["top"]) - np.array(res[nm]["mid"]),
                        "gap_b": np.array(res[nm]["bot"]) - np.array(res[nm]["mid"])})
    gy = dfy.groupby("y").mean()
    tail_worse_t = tm["top"] < tm["mid"] - 0.01
    tail_worse_b = tm["bot"] < tm["mid"] - 0.01
    cons_t = int((gy.gap_t < 0).sum()); cons_b = int((gy.gap_b < 0).sum())
    print(f"  {nm}: bot {tm['bot']:+.4f} mid {tm['mid']:+.4f} top {tm['top']:+.4f} "
          f"| top差距逐年负 {cons_t}/5 bot {cons_b}/5")
    verdict_a[nm] = (tail_worse_t and cons_t >= 4) or (tail_worse_b and cons_b >= 4)
P = np.nanmean(np.array(dec_prof), axis=0) * 1e4
print("\n== (b) 钱在哪一档(king 十分位, 去均值 bps) ==")
print("  D1..D10:", " ".join(f"{x:+.1f}" for x in P))
spread = P[9] - P[0]; edge = (P[9] - P[8]) + (P[1] - P[0])
share = edge / spread if spread != 0 else np.nan
print(f"  全距 D10−D1 {spread:+.2f} | 边缘贡献 (D10−D9)+(D2−D1) {edge:+.2f} = {share:.1%}")
va = verdict_a["king"]; vb = share >= 0.40
print(f"\n判: (a) 尾段有可挪差距 = {va} | (b) 边缘份额≥40% = {vb}")
print("★立项" if (va and vb) else "候选关闭 —— " +
      ("尾段排序不差于中段(无差距可挪)" if not va else "钱不在极端档(挪过去无回报)"))
print("TAILGATE_DONE")
