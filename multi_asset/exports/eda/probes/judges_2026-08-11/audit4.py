"""四处最脆的地方逐个实测(全部本地数据, 不依赖 jpline)。

① from_partial 的 −30bps: 对 mid_at_anchor 计 vs 对 mid_at_submit 计 —— 差多少?
   若换成提交时刻的参考价后大幅收窄 ⇒ 那 −30 里有一块是【参考价漂移】不是逆向选择,
   今天最大杠杆的尺寸要打折。
② funding_ema 口径: 实盘 preds_latest 与离线宽面板是否同一个量?
③ 意图书 vs 成交书: target_w 与实际成交的偏离有多大?
④ 换手对账: 回放 0.44-0.48/锚 vs 实盘 0.330 —— 差在哪?
"""
import json, glob, numpy as np, datetime as dt
import pandas as pd

LIVE = "/Users/haosiyu/dl_quant_live/state/live/pilot_log"
FEEFIX = dt.datetime(2026, 8, 5, 20, 0, tzinfo=dt.timezone.utc).timestamp()

rows = []
for f in sorted(glob.glob(f"{LIVE}/2026*/orders.jsonl")):
    for L in open(f):
        try: d = json.loads(L)
        except: continue
        rows.append(d)

# ═══ ① from_partial 的参考价问题 ═══
print("═"*74)
print("① from_partial 的 −30bps: 换参考价后还剩多少?")
def edge(d, ref):
    px, mid, side = d.get("avg_fill_px"), d.get(ref), d.get("side")
    if not px or not mid or mid <= 0 or side is None: return None
    s = +1.0 if str(side).lower().startswith("s") else -1.0
    return s * (px - mid) / mid * 1e4

for fam, sel in [("topup_taker/from_partial", lambda d: d.get("topup_source") == "from_partial"),
                 ("topup_taker/from_reject", lambda d: d.get("topup_source") == "from_reject"),
                 ("maker", lambda d: d.get("order_type") == "maker")]:
    F = [d for d in rows if sel(d) and (d.get("filled_notional") or 0) and abs(d["filled_notional"]) > 0
         and (d.get("submit_ts") or 0) >= FEEFIX]
    if len(F) < 10:
        print(f"  {fam:26s} n={len(F)} 太少"); continue
    n = np.array([abs(d["filled_notional"]) for d in F])
    ea = np.array([edge(d, "mid_at_anchor") or np.nan for d in F])
    es = np.array([edge(d, "mid_at_submit") or np.nan for d in F])
    oa = np.isfinite(ea); os_ = np.isfinite(es)
    wa = float(np.sum(n[oa]*ea[oa])/n[oa].sum()) if oa.any() else np.nan
    ws = float(np.sum(n[os_]*es[os_])/n[os_].sum()) if os_.any() else np.nan
    print(f"  {fam:26s} n={len(F):4d}  vs mid_at_anchor {wa:+8.2f}  "
          f"vs mid_at_submit {ws:+8.2f}  (覆盖 {os_.sum()}/{len(F)})  "
          f"⇒ 参考价漂移解释 {wa-ws:+8.2f} bps")

# ═══ ② funding_ema 口径 ═══
print("\n" + "═"*74)
print("② funding_ema 口径: 实盘 preds_latest vs 离线宽面板")
p = json.load(open("/Users/haosiyu/dl_quant_live/state/live/preds_latest.json"))
fe = p["funding_ema"]
v = np.array([fe[s] for s in p["symbols"] if s in fe], float)
print(f"  实盘: n={len(v)}  分位[1,25,50,75,99] = {np.nanpercentile(v,[1,25,50,75,99]).round(7)}")
print(f"        均值 {np.nanmean(v):+.3e}  sd {np.nanstd(v):.3e}  绝对值中位 {np.nanmedian(np.abs(v)):.3e}")
print(f"  ★ 离线宽面板的 funding_ema 在 jpline 上(当前拒连), 本次无法逐位对照。")
print(f"    可比的是【量级与分布形状】—— 记录在此供恢复后对账;")
print(f"    记忆 funding_settlement_interval_unit_bug 明确记着【两个口径是有意并存的】,")
print(f"    ⇒ 这是 C2 影子有效性的【前置未核实项】, 必须在读方向之前对上。")

# ═══ ③ 意图书 vs 成交书 ═══
print("\n" + "═"*74)
print("③ 意图书(target_w) vs 实际成交")
by = {}
for d in rows:
    rid = d.get("rebalance_id")
    if not rid: continue
    b = by.setdefault(rid, {"intend": 0.0, "filled": 0.0, "n_int": 0, "n_fill": 0})
    it = d.get("intended_notional"); fn = d.get("filled_notional")
    if it: b["intend"] += abs(float(it)); b["n_int"] += 1
    if fn: b["filled"] += abs(float(fn)); b["n_fill"] += 1
ok = [v for v in by.values() if v["intend"] > 100]
fr = np.array([v["filled"]/v["intend"] for v in ok])
print(f"  锚 {len(ok)}  成交名义 / 意图名义: 均值 {fr.mean():.3f}  中位 {np.median(fr):.3f}  "
      f"分位[10,90] {np.percentile(fr,[10,90]).round(3)}")
print(f"  ⇒ 意图书与成交书的名义额差 {100*(1-fr.mean()):.1f}% ——")
print(f"    我报的实盘 rank-IC 0.0509 与毛额 +1.28bps 都是【意图书】的, 不是成交书的。")

# ═══ ④ 换手对账 ═══
print("\n" + "═"*74)
print("④ 换手: 实盘实测 vs 回放")
TW, PW = {}, {}
for d in rows:
    rid, sym = d.get("rebalance_id"), d.get("symbol")
    if not rid or not sym: continue
    if d.get("target_w") is not None: TW.setdefault(rid, {})[sym] = float(d["target_w"])
    if d.get("prev_w") is not None: PW.setdefault(rid, {})[sym] = float(d["prev_w"])
t = []
for rid in TW:
    if rid not in PW: continue
    s = set(TW[rid]) | set(PW[rid])
    t.append(sum(abs(TW[rid].get(x, 0.0)-PW[rid].get(x, 0.0)) for x in s)/2.0)
t = np.array(t)
print(f"  实盘意图换手/锚: 均值 {t.mean():.3f}  中位 {np.median(t):.3f}  n={len(t)}")
print(f"  回放(引擎, 无风险预算): gross 1058.5/年 ÷ 2190 = {1058.5/2190:.3f}/锚")
print(f"                          net   961.0/年 ÷ 2190 = {961.0/2190:.3f}/锚")
print(f"  ⇒ 回放比实盘高 {100*(961.0/2190/t.mean()-1):.0f}%(净口径)")
print(f"    候选解释(未验证): min-notional 跳过 / 风险预算改变权重分布 / harvest EMA / 仓位上限")
print(f"    ★ 方向是【保守】的(回放高估换手 ⇒ 低估净额), 但未标定 ⇒ 不能说回放净额可直接读。")
