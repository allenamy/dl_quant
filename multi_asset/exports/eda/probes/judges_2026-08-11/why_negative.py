"""为什么 08-05 20:00Z → 08-06 20:00Z 连续 7 锚 IC 为负 —— 逐锚市场状态诊断。

只用实盘一手记录 + 本机 klines。不猜, 逐个假设配一个可测的量:
  A 市场同向: 横截面收益离散度塌缩 / 市场整体大幅移动 ⇒ 横截面信号无处发力
  B 反转 regime: 前一期收益与本期收益的横截面相关(自反转强度)
  C 少数名字主导: IC 的负值由几个大权重名字贡献?(逐名 w·r 的集中度)
  D 书的姿态: 换手 / 名字数 / gross / 有效名字数是否在负段异常
"""
import json, glob, numpy as np, pandas as pd, datetime as dt

LIVE = "/Users/haosiyu/dl_quant_live/state/live/pilot_log"
mids, tw, meta = {}, {}, {}
for f in sorted(glob.glob(f"{LIVE}/2026*/anchors.jsonl")):
    for L in open(f):
        try: d = json.loads(L)
        except: continue
        mv = d.get("mid_at_anchor_vector")
        if isinstance(mv, str):
            try: mv = json.loads(mv)
            except: mv = None
        if d.get("anchor_ts") and mv:
            k = round(float(d["anchor_ts"]))
            mids[k] = mv
            meta[k] = {"regime": d.get("regime_at_anchor"), "gross": d.get("target_gross"),
                       "nskip": d.get("n_names_skipped")}
for f in sorted(glob.glob(f"{LIVE}/2026*/orders.jsonl")):
    for L in open(f):
        try: d = json.loads(L)
        except: continue
        if d.get("target_w") is not None and d.get("symbol") and d.get("anchor_ts"):
            tw.setdefault(round(float(d["anchor_ts"])), {})[d["symbol"]] = float(d["target_w"])

keys = sorted(mids)
rows = []
for i, a in enumerate(keys[:-1]):
    if a not in tw: continue
    m0, m1 = mids[a], mids[keys[i+1]]
    prev = mids[keys[i-1]] if i > 0 else None
    w = tw[a]
    s = [x for x in w if x in m0 and x in m1 and m0[x] and m1[x] > 0 and abs(w[x]) > 1e-12]
    if len(s) < 10: continue
    wv = np.array([w[x] for x in s]); rv = np.array([m1[x]/m0[x]-1 for x in s])
    ic = float(pd.Series(wv).corr(pd.Series(rv), method="spearman"))
    contrib = wv*rv
    g = np.abs(wv).sum()
    # A 市场同向 / 离散度
    mkt = float(np.mean(rv)); disp = float(np.std(rv))
    # B 自反转: 上一期收益 vs 本期收益的横截面相关
    rev = np.nan
    if prev is not None:
        s2 = [x for x in s if x in prev and prev[x]]
        if len(s2) >= 20:
            r_prev = np.array([m0[x]/prev[x]-1 for x in s2])
            r_now = np.array([m1[x]/m0[x]-1 for x in s2])
            rev = float(pd.Series(r_prev).corr(pd.Series(r_now), method="spearman"))
    # C 贡献集中度: 前 5 名字占 |总贡献| 的比例
    o = np.argsort(-np.abs(contrib))
    top5 = float(np.abs(contrib[o[:5]]).sum()/max(np.abs(contrib).sum(), 1e-12))
    rows.append({"ts": a, "t": dt.datetime.fromtimestamp(a, dt.timezone.utc), "n": len(s),
                 "ic": ic, "pnl_bps": float(contrib.sum()/g*1e4),
                 "mkt_ret_bps": mkt*1e4, "disp_bps": disp*1e4, "self_rev": rev,
                 "top5_share": top5, "regime": meta[a]["regime"], "gross": meta[a]["gross"]})
df = pd.DataFrame(rows).sort_values("ts").reset_index(drop=True)

NEG0 = dt.datetime(2026, 8, 5, 19, tzinfo=dt.timezone.utc)
NEG1 = dt.datetime(2026, 8, 6, 21, tzinfo=dt.timezone.utc)
df["blk"] = np.where((df.t >= NEG0) & (df.t <= NEG1), "负段(7锚)",
                     np.where(df.t < NEG0, "换装前后正段", "其后"))

print("═"*78)
print("逐段对照 —— 每个假设配一个可测的量")
print("═"*78)
agg = df.groupby("blk").agg(n=("ic", "size"), ic=("ic", "mean"), pnl=("pnl_bps", "mean"),
                            mkt=("mkt_ret_bps", "mean"), absmkt=("mkt_ret_bps", lambda x: np.mean(np.abs(x))),
                            disp=("disp_bps", "mean"), selfrev=("self_rev", "mean"),
                            top5=("top5_share", "mean"), names=("n", "mean"))
print(agg.round(4).to_string())

print("\n" + "═"*78)
print("全样本相关: 各诊断量 vs 逐锚 IC")
print("═"*78)
for k, lbl in [("mkt_ret_bps", "A 市场收益(带符号)"), ("disp_bps", "A 横截面离散度"),
               ("self_rev", "B 自反转强度"), ("top5_share", "C 前5名字贡献占比"),
               ("n", "D 名字数")]:
    v = df[k].values; ok = np.isfinite(v) & np.isfinite(df.ic.values)
    if ok.sum() > 10:
        sp = pd.Series(df.ic.values[ok]).corr(pd.Series(v[ok]), method="spearman")
        print(f"  ρ(IC, {lbl:20s}) = {sp:+.4f}   n={ok.sum()}")
ab = np.abs(df.mkt_ret_bps.values); ok = np.isfinite(ab)
print(f"  ρ(IC, A 市场收益【绝对值】)   = "
      f"{pd.Series(df.ic.values[ok]).corr(pd.Series(ab[ok]), method='spearman'):+.4f}")

print("\n" + "═"*78)
print("IC 的自相关(能不能事后择时)")
print("═"*78)
ic = df.ic.values
for lag in (1, 2, 3):
    a, b = ic[:-lag], ic[lag:]
    print(f"  AR({lag}) = {np.corrcoef(a, b)[0,1]:+.4f}")
print(f"  连续同号最长游程: 负 {max((len(list(g)) for k,g in __import__('itertools').groupby(ic<0) if k), default=0)}  "
      f"正 {max((len(list(g)) for k,g in __import__('itertools').groupby(ic>0) if k), default=0)}")

print("\n" + "═"*78)
print("负段逐锚明细")
print("═"*78)
sub = df[df.blk == "负段(7锚)"]
print(sub[["t", "ic", "pnl_bps", "mkt_ret_bps", "disp_bps", "self_rev", "top5_share", "regime"]].to_string(index=False))
df.to_csv("/Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/6737834a-f0b4-40e0-82a0-c0e83c0ccf5f/scratchpad/why_negative.csv", index=False)
