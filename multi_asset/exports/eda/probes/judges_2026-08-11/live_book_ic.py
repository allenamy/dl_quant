"""从实盘一手记录重建【在役整书】的逐锚 rank-IC 与已实现收益。

为什么自己重建: state/factor_health_last.json = {"ok": false, "reason": "report_unreachable"}
—— 影子监视报告住在远端研究机(jpline, 正在拒连)⇒ 在役逐锚 IC 序列当前【不可读】。
本脚本只用实盘本地记录, 不依赖任何远端。

口径(逐条说明, 因为口径就是结论的一半):
  权重 = orders.jsonl 的 target_w —— 这是【书真正打算持有的】(已过 cap/风险预算/harvest EMA, 单位 L1)
  收益 = 相邻锚的 mid_at_anchor_vector 之比 −1 —— 4h 已实现, 与书的持有期对齐
  rank-IC = 该锚可交易集上 Spearman(target_w, 已实现收益)
  ★ 不做横截面去均值: 书本身已 demean(市场中性), 直接算即可
  ★ 换装分界: 2026-08-05 (S2 世代 + 因果面板) —— 前后必须分开报, 合并会把两个模型混成一个数
"""
import json, glob, datetime as dt
import numpy as np
import pandas as pd

LIVE = "/Users/haosiyu/dl_quant_live/state/live/pilot_log"
SWAP = dt.datetime(2026, 8, 5, tzinfo=dt.timezone.utc).timestamp()

anch = {}
for f in sorted(glob.glob(f"{LIVE}/2026*/anchors.jsonl")):
    for L in open(f):
        try: d = json.loads(L)
        except: continue
        rid = d.get("rebalance_id")
        mv = d.get("mid_at_anchor_vector")
        if isinstance(mv, str):
            try: mv = json.loads(mv)
            except: mv = None
        if rid and mv:
            anch[rid] = {"ts": d.get("anchor_ts") or 0, "mid": mv,
                         "regime": d.get("regime_at_anchor"), "gross": (d.get("target_gross") or 0)}
seq = sorted(anch.items(), key=lambda kv: kv[1]["ts"])
nxt = {a[0]: b for a, b in zip(seq[:-1], seq[1:])}
print(f"锚点(带 mid 向量) {len(seq)}  可取下一锚 {len(nxt)}")

W = {}
for f in sorted(glob.glob(f"{LIVE}/2026*/orders.jsonl")):
    for L in open(f):
        try: d = json.loads(L)
        except: continue
        rid, sym, tw = d.get("rebalance_id"), d.get("symbol"), d.get("target_w")
        if rid and sym and tw is not None:
            W.setdefault(rid, {})[sym] = float(tw)
print(f"有 target_w 的锚 {len(W)}")

rows = []
for rid, a in seq:
    nb = nxt.get(rid)
    if nb is None or rid not in W:
        continue
    w = W[rid]; m0 = a["mid"]; m1 = nb[1]["mid"]
    syms = [s for s in w if s in m0 and s in m1 and m0[s] and m1[s] > 0 and abs(w[s]) > 1e-12]
    if len(syms) < 10:
        continue
    wv = np.array([w[s] for s in syms])
    rv = np.array([m1[s]/m0[s] - 1.0 for s in syms])
    ok = np.isfinite(wv) & np.isfinite(rv)
    if ok.sum() < 10:
        continue
    ic = float(pd.Series(wv[ok]).corr(pd.Series(rv[ok]), method="spearman"))
    g = float(np.abs(wv[ok]).sum())
    pnl_bps = float(np.sum(wv[ok]*rv[ok]) / max(g, 1e-12) * 1e4)   # 每单位 gross 的毛收益(bps)
    rows.append({"rid": rid, "ts": a["ts"], "n": int(ok.sum()), "ic": ic,
                 "gross_bps": pnl_bps, "regime": a["regime"],
                 "post_swap": a["ts"] >= SWAP})

df = pd.DataFrame(rows).sort_values("ts")
print(f"\n可评锚 {len(df)}  时间 "
      f"{dt.datetime.fromtimestamp(df.ts.min(), dt.timezone.utc):%m-%d %H:%MZ} → "
      f"{dt.datetime.fromtimestamp(df.ts.max(), dt.timezone.utc):%m-%d %H:%MZ}")


def rep(sub, tag):
    if len(sub) < 3:
        print(f"\n[{tag}] 锚 {len(sub)} —— 太少, 不出具"); return
    ic = sub.ic.values; g = sub.gross_bps.values
    se = ic.std(ddof=1)/np.sqrt(len(ic))
    print(f"\n[{tag}] 锚 {len(sub)}  名字/锚 {sub.n.mean():.0f}")
    print(f"  rank-IC  均值 {ic.mean():+.4f}  sd {ic.std(ddof=1):.4f}  SE {se:.4f}  "
          f"t={ic.mean()/max(se,1e-9):+.2f}  正号 {100*(ic>0).mean():.0f}%")
    print(f"  毛收益   均值 {g.mean():+.2f} bps/锚  合计 {g.sum():+.1f} bps  "
          f"正号 {100*(g>0).mean():.0f}%")
    # 扣实测成本: 换手未知(需 prev_w), 用实测总成本 3.115 bps × 假定每锚换手 0.35 作粗算
    print(f"  ★ 净额不在此出具 —— 需逐锚真实换手, 见下方单列")


rep(df, "全部实盘锚")
rep(df[~df.post_swap], "换装前 (<08-05)")
rep(df[df.post_swap], "★ 换装后 (≥08-05, 在役 S2 世代)")

# 逐锚换手(从 prev_w 与 target_w)
TW, PW = {}, {}
for f in sorted(glob.glob(f"{LIVE}/2026*/orders.jsonl")):
    for L in open(f):
        try: d = json.loads(L)
        except: continue
        rid, sym = d.get("rebalance_id"), d.get("symbol")
        if not rid or not sym: continue
        if d.get("target_w") is not None: TW.setdefault(rid, {})[sym] = float(d["target_w"])
        if d.get("prev_w") is not None: PW.setdefault(rid, {})[sym] = float(d["prev_w"])
turn = {}
for rid in TW:
    if rid not in PW: continue
    s = set(TW[rid]) | set(PW[rid])
    turn[rid] = sum(abs(TW[rid].get(x, 0.0) - PW[rid].get(x, 0.0)) for x in s) / 2.0
df["turn"] = df.rid.map(turn)
sub = df[df.turn.notna()]
if len(sub) >= 3:
    for c in (3.115, 5.80):
        net = sub.gross_bps - sub.turn*2*c        # 双边: |Δw| 之和的一半 × 2 × cost
        print(f"\n[净额 @{c}bps] 锚 {len(sub)}  换手/锚 {sub.turn.mean():.3f}  "
              f"净 {net.mean():+.2f} bps/锚  合计 {net.sum():+.1f} bps  正号 {100*(net>0).mean():.0f}%")
print("\n★ 夏普不出具 —— 实盘仅 9 天, 日频夏普在这个样本上不是估计量, 是噪声。")
df.to_csv("/Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/6737834a-f0b4-40e0-82a0-c0e83c0ccf5f/scratchpad/live_book_ic.csv", index=False)
print("LIVEIC_DONE")
