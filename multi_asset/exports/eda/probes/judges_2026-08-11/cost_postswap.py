"""换装后(2026-08-05+)真实成本重建 —— 一手成交, LIVE 树(不是 DRY_RUN 树)。
★ 路径写死绝对路径: state/live/pilot_log, 不是 state/pilot_log(后者是干跑, fee_source 自称 N/A)。
"""
import json, glob, datetime as dt, collections
import numpy as np

LIVE = "/Users/haosiyu/dl_quant_live/state/live/pilot_log"
SWAP = dt.datetime(2026, 8, 5, tzinfo=dt.timezone.utc).timestamp()
FEEFIX = dt.datetime(2026, 8, 5, 20, 0, tzinfo=dt.timezone.utc).timestamp()   # STATE: 完整费链端到端首验
CLEAN = dt.datetime(2026, 8, 6, tzinfo=dt.timezone.utc).timestamp()

rows = []
for f in sorted(glob.glob(f"{LIVE}/2026080*/orders.jsonl")):
    for L in open(f):
        try: rows.append(json.loads(L))
        except: pass
print(f"orders 总行 {len(rows)}")

def edge_bps(d):
    px, mid, side = d.get("avg_fill_px"), d.get("mid_at_anchor"), d.get("side")
    if not px or not mid or mid <= 0 or side is None: return None
    s = +1.0 if str(side).lower().startswith("s") else -1.0     # 卖: 成交价高于 mid 有利
    return s * (px - mid) / mid * 1e4

def window(rows, t0, label):
    F = [d for d in rows if (d.get("filled_notional") or 0) and abs(d["filled_notional"]) > 0
         and (d.get("submit_ts") or d.get("anchor_ts") or 0) >= t0]
    if not F:
        print(f"\n[{label}] 无成交行"); return
    notl = np.array([abs(d["filled_notional"]) for d in F])
    fee = np.array([float(d.get("fee_paid") or 0.0) for d in F])
    allusdt = [d.get("fee_all_usdt") for d in F]
    n_bad = sum(1 for x in allusdt if x is False)
    fee_bps = fee.sum() / notl.sum() * 1e4
    e = np.array([edge_bps(d) if edge_bps(d) is not None else np.nan for d in F])
    ok = np.isfinite(e)
    edge_w = float(np.sum(notl[ok] * e[ok]) / notl[ok].sum())
    print(f"\n[{label}]  成交行 {len(F)}  名义额 {notl.sum():,.0f} USDT  "
          f"(fee_all_usdt=False 的行 {n_bad})")
    print(f"  手续费     {fee_bps:+7.3f} bps   (总费 {fee.sum():.4f} USDT)")
    print(f"  执行 edge  {edge_w:+7.3f} bps   (正=对我们有利, 名义额加权, 覆盖 {ok.sum()}/{len(F)})")
    print(f"  ⇒ 总成本   {fee_bps - edge_w:+7.3f} bps")
    by = collections.defaultdict(lambda: [0.0, 0.0, 0.0])
    for d, n_, ee in zip(F, notl, e):
        k = d.get("order_type", "?")
        if k == "topup_taker":
            k += "/" + str(d.get("topup_source", "未标源"))
        by[k][0] += n_
        by[k][1] += float(d.get("fee_paid") or 0.0)
        if np.isfinite(ee): by[k][2] += n_ * ee
    print("  ── 分族 ──")
    for k, (n_, f_, we) in sorted(by.items(), key=lambda x: -x[1][0]):
        print(f"    {k:26s} 名义 {n_:10,.0f}  费 {f_/n_*1e4:+6.3f}bps  edge {we/n_:+8.3f}bps  "
              f"净 {f_/n_*1e4 - we/n_:+7.3f}bps")

window(rows, SWAP,   "换装后 全部 (08-05 00:00Z+)")
window(rows, FEEFIX, "★换装后 费链已验 (08-05 20:00Z+)")
window(rows, CLEAN,  "换装后 完整日 (08-06 00:00Z+)")

# BNB 抵扣核验: 从 fills 侧独立看 commission_asset
ca = collections.Counter(); mk = collections.Counter()
for f in sorted(glob.glob(f"{LIVE}/2026080[56789]/fills.jsonl")):
    for L in open(f):
        try: d = json.loads(L)
        except: continue
        if (d.get("fill_ts") or 0) >= FEEFIX:
            ca[d.get("commission_asset")] += 1
            mk[bool(d.get("venue_maker_flag"))] += 1
print(f"\n[BNB 抵扣核验, 费链已验窗] commission_asset 分布 {dict(ca)}  maker/taker 笔数 {dict(mk)}")
