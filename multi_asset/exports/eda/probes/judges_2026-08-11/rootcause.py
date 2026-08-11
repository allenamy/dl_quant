"""负段(08-05 20:00Z → 08-06 20:00Z, 7 锚)的根因排查 —— 四个可单独证伪的测试。

部署时点: 08-05 19:06Z (deff3bb, S2 世代包: 模型/口径/风险预算/费率四位一体)

T1 过渡效应: 换模型那几锚要把旧仓换成新仓 ⇒ 换手应有【一次性尖峰】; 且成交书应比意图书差得多
T2 风险预算签名: 风险预算按 1/波动 重加权 ⇒ 权重与 rvol 的关系应在部署点【突变】
T3 书的性格是否变了: 部署前后 target_w 的自相似度(与上一锚的秩相关)
T4 负段的 IC 是不是"全面的": 逐名贡献的符号分布, 以及多空两侧分别的 IC
"""
import json, glob, numpy as np, pandas as pd, datetime as dt

LIVE = "/Users/haosiyu/dl_quant_live/state/live/pilot_log"
DEPLOY = dt.datetime(2026, 8, 5, 19, 6, tzinfo=dt.timezone.utc).timestamp()
NEG0 = dt.datetime(2026, 8, 5, 19, 30, tzinfo=dt.timezone.utc).timestamp()
NEG1 = dt.datetime(2026, 8, 6, 21, 0, tzinfo=dt.timezone.utc).timestamp()

mids, tw, rb = {}, {}, {}
for f in sorted(glob.glob(f"{LIVE}/2026*/anchors.jsonl")):
    for L in open(f):
        try: d = json.loads(L)
        except: continue
        mv = d.get("mid_at_anchor_vector")
        if isinstance(mv, str):
            try: mv = json.loads(mv)
            except: mv = None
        if d.get("anchor_ts") and mv: mids[round(float(d["anchor_ts"]))] = mv
for f in sorted(glob.glob(f"{LIVE}/2026*/orders.jsonl")):
    for L in open(f):
        try: d = json.loads(L)
        except: continue
        a = d.get("anchor_ts")
        if a and d.get("symbol") and d.get("target_w") is not None:
            tw.setdefault(round(float(a)), {})[d["symbol"]] = float(d["target_w"])
for f in sorted(glob.glob(f"{LIVE}/2026*/position_readback.jsonl")):
    for L in open(f):
        try: d = json.loads(L)
        except: continue
        a = d.get("anchor_ts"); v = d.get("venue_position_notional")
        if a and d.get("symbol") and v is not None:
            rb.setdefault(round(float(a)), {})[d["symbol"]] = float(v)

K = sorted(mids)
def seg(ts): return "负段" if NEG0 <= ts <= NEG1 else ("部署前" if ts < NEG0 else "部署后-恢复")

rows = []
for i, a in enumerate(K[:-1]):
    if a not in tw: continue
    m0, m1 = mids[a], mids[K[i+1]]
    w = tw[a]; prevw = tw.get(K[i-1]) if i > 0 else None
    s = [x for x in w if x in m0 and x in m1 and m0[x] and m1[x] > 0 and abs(w[x]) > 1e-12]
    if len(s) < 20: continue
    wv = np.array([w[x] for x in s]); rv = np.array([m1[x]/m0[x]-1 for x in s])
    ic = float(pd.Series(wv).corr(pd.Series(rv), method="spearman"))
    # T1 换手
    turn = np.nan; selfsim = np.nan
    if prevw:
        u = sorted(set(w) | set(prevw))
        turn = sum(abs(w.get(x, 0.)-prevw.get(x, 0.)) for x in u)/2
        c = [x for x in u if x in w and x in prevw]
        if len(c) >= 20:
            selfsim = float(pd.Series([w[x] for x in c]).corr(pd.Series([prevw[x] for x in c]), method="spearman"))
    # T1b 成交书 IC
    ic_rb = np.nan
    if a in rb:
        b = rb[a]; s2 = [x for x in b if x in m0 and x in m1 and m0[x] and m1[x] > 0 and abs(b[x]) > 1e-9]
        if len(s2) >= 20:
            bv = np.array([b[x] for x in s2]); br = np.array([m1[x]/m0[x]-1 for x in s2])
            ic_rb = float(pd.Series(bv).corr(pd.Series(br), method="spearman"))
    # T4 多空两侧分别 IC + 贡献符号
    lo = wv < 0; hi = wv > 0
    ic_long = float(pd.Series(wv[hi]).corr(pd.Series(rv[hi]), method="spearman")) if hi.sum() >= 15 else np.nan
    ic_short = float(pd.Series(wv[lo]).corr(pd.Series(rv[lo]), method="spearman")) if lo.sum() >= 15 else np.nan
    ctr = wv*rv
    frac_pos = float((ctr > 0).mean())
    rows.append({"ts": a, "t": dt.datetime.fromtimestamp(a, dt.timezone.utc), "seg": seg(a),
                 "ic": ic, "ic_rb": ic_rb, "turn": turn, "selfsim": selfsim,
                 "ic_long": ic_long, "ic_short": ic_short, "frac_pos": frac_pos,
                 "pnl_long": float(ctr[hi].sum()/max(np.abs(wv).sum(),1e-12)*1e4),
                 "pnl_short": float(ctr[lo].sum()/max(np.abs(wv).sum(),1e-12)*1e4)})
d = pd.DataFrame(rows)

print("═"*84); print("T1/T3  部署边界前后的逐锚(换手 · 自相似 · 意图IC · 成交IC)"); print("═"*84)
w = d[(d.t >= dt.datetime(2026,8,5,8,tzinfo=dt.timezone.utc)) & (d.t <= dt.datetime(2026,8,7,8,tzinfo=dt.timezone.utc))]
print(w[["t","seg","turn","selfsim","ic","ic_rb"]].to_string(index=False, float_format=lambda x: f"{x:+.4f}"))

print("\n" + "═"*84); print("分段汇总"); print("═"*84)
g = d.groupby("seg").agg(n=("ic","size"), ic=("ic","mean"), ic_rb=("ic_rb","mean"),
                         turn=("turn","mean"), selfsim=("selfsim","mean"),
                         ic_long=("ic_long","mean"), ic_short=("ic_short","mean"),
                         pnl_long=("pnl_long","mean"), pnl_short=("pnl_short","mean"),
                         frac_pos=("frac_pos","mean"))
print(g.round(4).to_string())

print("\n" + "═"*84); print("★ T1 判读: 过渡效应应表现为 —— 部署首锚换手尖峰 + 负段成交IC << 意图IC"); print("═"*84)
b = d[d.seg=="负段"]
print(f"  负段: 意图IC {b.ic.mean():+.4f}  成交IC {b.ic_rb.mean():+.4f}  差 {b.ic_rb.mean()-b.ic.mean():+.4f}")
o = d[d.seg!="负段"]
print(f"  其余: 意图IC {o.ic.mean():+.4f}  成交IC {o.ic_rb.mean():+.4f}  差 {o.ic_rb.mean()-o.ic.mean():+.4f}")
fst = d[d.t >= dt.datetime.fromtimestamp(DEPLOY, dt.timezone.utc)].head(1)
print(f"  部署后首锚换手 {fst.turn.values[0] if len(fst) else float('nan'):.4f}  "
      f"vs 全期均值 {d.turn.mean():.4f}  vs 负段均值 {b.turn.mean():.4f}")

print("\n" + "═"*84); print("★ T4 判读: 负段是多头侧还是空头侧亏的"); print("═"*84)
print(f"  负段  多头IC {b.ic_long.mean():+.4f} / 空头IC {b.ic_short.mean():+.4f}   "
      f"多头pnl {b.pnl_long.mean():+.2f}bps / 空头pnl {b.pnl_short.mean():+.2f}bps")
print(f"  其余  多头IC {o.ic_long.mean():+.4f} / 空头IC {o.ic_short.mean():+.4f}   "
      f"多头pnl {o.pnl_long.mean():+.2f}bps / 空头pnl {o.pnl_short.mean():+.2f}bps")
d.to_csv("/Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/6737834a-f0b4-40e0-82a0-c0e83c0ccf5f/scratchpad/rootcause.csv", index=False)
