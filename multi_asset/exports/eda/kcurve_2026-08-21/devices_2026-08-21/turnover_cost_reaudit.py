#!/usr/bin/env python3
"""T1 · 换手/节奏成本模型复审 —— 实盘实测【成交 + 未成交】联合成本分布 (DESIGN_optimization_path §3.4-1)

> 创建: 2026-08-22 | Session: 6737834a-T1 | 状态: 判官脚本(可重跑, 只读实盘日志, 只写本目录 results/)
> 作废条件: 实盘 orders/fills 字段语义变更(见 docs/FIELD_CALIBERS_2026-08-19.md), 或挂单/补单政策变更

输入(全部只读; SHA256 写进输出 json 的 `inputs` 块):
  ~/dl_quant_live/state/live/pilot_log/2026*/{orders,fills,anchors,daily_nav}.jsonl   ← LIVE 树(带 live/ 段)
  ~/guard_twin/state/income.jsonl                                                      ← 账户 income 账本(手续费真值)
输出:
  results/turnover_cost_reaudit_2026-08-21.json

口径(全部 bps, 正 = 对我们是成本; 方向号 s=+1 买 / −1 卖):
  maker 滑点       s·(avg_fill_px/mid − 1)·1e4, mid ∈ {mid_at_submit, mid_at_anchor} 两口径都给
  补单漂移         topup_taker 行 avg_fill_px 对 mid_at_submit(= 该名 maker 单提交时 mid, 非补单时刻 mid; 见
                   binance_executor.topup: topup_leg=dict(p,**_fresh) 只重置成交字段) / mid_at_anchor / intended_limit_px
  手续费           主源 = fills.jsonl 去重后逐笔 commission(我们自己的 trade_id; BNB 按最近锚 BNBUSDT 中价折 USDT);
                   账本 income.jsonl COMMISSION 行按 (symbol, |Δt|≤3s) 与 fills 配对作对账(同账户还有 λ探针/止损/平仓成交,
                   账本不分来源 ⇒ 不能直接按时间窗归锚 —— 首版这么做把 08-21 12:16Z 平仓 12.9U 与探针费记进了 12:00Z 锚);
                   orders.fee_paid 第三路对账
  未补单残差机会成本 s_res·(mid_next_anchor/mid_at_anchor − 1)·1e4 × |残差|, 到下一锚的方向性漂移(非现金; 单列)
  每单位换手全口径成本 = (账本费 + maker 滑点$ + 补单漂移$) / 成交额   以及 / 意图额 两分母都给
锚分类: normal / rebuild(整书重建, 意图换手比≥0.8) / resize(入金扩容锚) / flatten(protective_flatten)
★ fills.jsonl trade_id 重复 = 回填副本: 金额取一次, markout 取有值那条(memory fills_jsonl_duplicate_trade_ids)
"""
from __future__ import annotations
import glob, hashlib, json, os, sys, datetime as dt
from collections import defaultdict, OrderedDict
import numpy as np
import pandas as pd

HOME = os.path.expanduser("~")
LOG = f"{HOME}/dl_quant_live/state/live/pilot_log"
INCOME = f"{HOME}/guard_twin/state/income.jsonl"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "results", "turnover_cost_reaudit_2026-08-21.json")

T_START = dt.datetime(2026, 8, 5, 12, 0, tzinfo=dt.timezone.utc).timestamp() - 600   # 换装边界 08-05 12:00Z
T_END = dt.datetime(2026, 8, 21, 16, 30, tzinfo=dt.timezone.utc).timestamp()         # 含 08-21 16:00Z 重建锚
T_INSERVICE = dt.datetime(2026, 8, 10, 11, 50, tzinfo=dt.timezone.utc).timestamp()    # α=0.05+带 首锚 12:00Z
T_BANDIT = dt.datetime(2026, 8, 12, 3, 50, tzinfo=dt.timezone.utc).timestamp()        # ε-赌博机首锚 04:00Z
# 已知结构性锚(入金扩容), 由 daily_nav external_flow 同日首锚核对
KNOWN_RESIZE = {"2026-08-10T08", "2026-08-18T04"}
BNB_FALLBACK = 616.0


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def iso(t):
    return dt.datetime.fromtimestamp(float(t), dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def hourkey(t):
    return dt.datetime.fromtimestamp(float(t), dt.timezone.utc).strftime("%Y-%m-%dT%H")


def jl(path):
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def wmean(x, w):
    x = np.asarray(x, float); w = np.asarray(w, float)
    ok = np.isfinite(x) & np.isfinite(w) & (w > 0)
    return float((x[ok] * w[ok]).sum() / w[ok].sum()) if w[ok].sum() > 0 else float("nan")


def boot_ci(series, nb=3000, block=6, seed=11):
    """锚级块 bootstrap(块=6 锚≈1 天), 均值 CI95。"""
    d = np.asarray(series, float); d = d[np.isfinite(d)]
    L = len(d)
    if L < 4:
        return [float("nan"), float("nan")]
    rng = np.random.default_rng(seed); k = int(np.ceil(L / block)); o = np.empty(nb)
    for q in range(nb):
        st = rng.integers(0, max(L - block, 1), size=k)
        ix = (st[:, None] + np.arange(block)[None, :]).ravel()[:L]; ix = ix[ix < L]
        o[q] = d[ix].mean()
    return [round(float(np.percentile(o, 2.5)), 4), round(float(np.percentile(o, 97.5)), 4)]


def stats(series):
    d = np.asarray(series, float); d = d[np.isfinite(d)]
    if len(d) == 0:
        return {}
    return {"n": int(len(d)), "mean": round(float(d.mean()), 4), "median": round(float(np.median(d)), 4),
            "sd": round(float(d.std(ddof=1)) if len(d) > 1 else float("nan"), 4),
            "p10": round(float(np.percentile(d, 10)), 4), "p90": round(float(np.percentile(d, 90)), 4),
            "ci95_mean_block6": boot_ci(d)}


# ───────────────────────── 1. 载入 ─────────────────────────
inputs = {}
files = {k: sorted(glob.glob(f"{LOG}/2026*/{k}.jsonl")) for k in ("orders", "fills", "anchors", "daily_nav")}
for k, fs in files.items():
    for p in fs:
        inputs[os.path.relpath(p, HOME)] = sha(p)
inputs[os.path.relpath(INCOME, HOME)] = sha(INCOME)

anchors = []
for p in files["anchors"]:
    for d in jl(p):
        mids = d.get("mid_at_anchor_vector")
        if isinstance(mids, str):
            try:
                mids = json.loads(mids)
            except Exception:
                mids = {}
        anchors.append({"rid": d["rebalance_id"], "ts": float(d["anchor_ts"]), "regime": d.get("regime_at_anchor"),
                        "halted": bool(d.get("opening_halted")), "target_gross": d.get("target_gross"),
                        "venue_gross": d.get("venue_gross_usdt"), "mids": mids or {}})
anchors.sort(key=lambda a: a["ts"])
A_BY_RID = {a["rid"]: a for a in anchors}

nav_by_day = {}
for p in files["daily_nav"]:
    last = None
    for d in jl(p):
        last = d
    if last:
        nav_by_day[last["day"]] = last

orders = []
for p in files["orders"]:
    for d in jl(p):
        orders.append(d)
fills_raw = []
for p in files["fills"]:
    for d in jl(p):
        fills_raw.append(d)

# ───────────────────────── 2. 锚时间线 + 分类 ─────────────────────────
rid_ts = {}
for o in orders:
    rid_ts.setdefault(o["rebalance_id"], float(o["anchor_ts"]))
timeline = sorted(rid_ts.items(), key=lambda x: x[1])           # (rid, ts) 含 FLATTEN-*
reg_anchors = [(r, t) for r, t in timeline if not r.startswith("FLATTEN")]
next_reg = {}
for i, (r, t) in enumerate(reg_anchors):
    next_reg[r] = reg_anchors[i + 1][0] if i + 1 < len(reg_anchors) else None

# 意图换手比 = Σ|intended_full|(每 (rid,symbol) 取一次) / target_gross
intended_by_rid = defaultdict(dict)
for o in orders:
    if o["order_type"] == "maker" and o.get("intended_full") is not None:
        key = o["symbol"]
        if key not in intended_by_rid[o["rebalance_id"]]:
            intended_by_rid[o["rebalance_id"]][key] = abs(float(o["intended_full"]))


def classify(rid, ts):
    if rid.startswith("FLATTEN"):
        return "flatten", None
    a = A_BY_RID.get(rid)
    tg = (a or {}).get("target_gross") or 0.0
    intended = sum(intended_by_rid.get(rid, {}).values())
    ratio = intended / tg if tg else float("nan")
    if hourkey(ts) in KNOWN_RESIZE:
        return "resize", ratio
    if np.isfinite(ratio) and ratio >= 0.8:
        return "rebuild", ratio
    return "normal", ratio


ANCHOR_INFO = OrderedDict()
for rid, ts in timeline:
    cls, ratio = classify(rid, ts)
    a = A_BY_RID.get(rid, {})
    ANCHOR_INFO[rid] = {"ts": ts, "iso": iso(ts), "class": cls, "intended_turnover_ratio": (None if ratio is None or not np.isfinite(ratio) else round(ratio, 4)),
                        "regime": a.get("regime"), "halted": a.get("halted"), "target_gross": a.get("target_gross"),
                        "venue_gross": a.get("venue_gross"),
                        "period": ("pre_inservice" if ts < T_INSERVICE else "inservice"),
                        "in_window": bool(T_START <= ts <= T_END)}

# ───────────────────────── 3. BNB 折算价 ─────────────────────────
bnb_series = sorted([(a["ts"], a["mids"].get("BNBUSDT")) for a in anchors if a["mids"].get("BNBUSDT")])


def bnb_px(ts):
    """最近(≤ts)锚的 BNBUSDT 中价; 无则回落最近任意锚; 再无则 616。"""
    if not bnb_series:
        return BNB_FALLBACK
    best = None
    for t, px in bnb_series:
        if t <= ts:
            best = px
        else:
            break
    return best if best else bnb_series[0][1]


# ───────────────────────── 4. 手续费: 账本行(对账用; 配对在 §5 之后) ─────────────────────────
ledger_rows = []
for d in jl(INCOME):
    if d.get("type") != "COMMISSION":
        continue
    t = float(d["time"]) / 1000.0
    amt = -float(d["income"])                                   # 出账为负 ⇒ 费为正
    if d.get("asset") == "BNB":
        amt *= bnb_px(t)
    elif d.get("asset") != "USDT":
        continue
    ledger_rows.append((t, d.get("symbol"), amt))

# ───────────────────────── 5. fills 去重 + 按腿拆费 + markout ─────────────────────────
fills_by_tid = {}
for f in fills_raw:
    tid = f.get("trade_id")
    cur = fills_by_tid.get(tid)
    if cur is None:
        fills_by_tid[tid] = dict(f)
    else:
        # 金额/价格/佣金取一次(已存在), markout 取有值那条
        if cur.get("mid_at_fill_plus_60s") is None and f.get("mid_at_fill_plus_60s") is not None:
            cur["mid_at_fill_plus_60s"] = f["mid_at_fill_plus_60s"]
fills = list(fills_by_tid.values())
fills_fee_by_rid_leg = defaultdict(lambda: defaultdict(float))
fills_notional_by_rid_leg = defaultdict(lambda: defaultdict(float))
markout_rows = []   # (rid, order_type, notional, markout_bps)
for f in fills:
    rid = f["rebalance_id"]; leg = f["order_type"]
    c = float(f.get("commission") or 0.0)
    if f.get("commission_asset") == "BNB":
        c *= bnb_px(float(f["fill_ts"]))
    fills_fee_by_rid_leg[rid][leg] += c
    fn = abs(float(f.get("fill_notional") or 0.0))
    fills_notional_by_rid_leg[rid][leg] += fn
    m60 = f.get("mid_at_fill_plus_60s")
    if isinstance(m60, (int, float)) and m60 and f.get("fill_px"):
        s = 1.0 if f["side"] == "buy" else -1.0
        markout_rows.append((rid, leg, fn, s * (float(m60) / float(f["fill_px"]) - 1.0) * 1e4))

# 账本 ↔ fills 配对(symbol 相同且 |Δt|≤3s): 配对上的归到该 fill 的 rid; 配不上的 = 平仓/探针/止损等非本书成交
import bisect
_sym_fills = defaultdict(list)
for f in fills:
    _sym_fills[f["symbol"]].append((float(f["fill_ts"]), f["rebalance_id"]))
for k_ in _sym_fills:
    _sym_fills[k_].sort()
ledger_fee_by_rid = defaultdict(float)
ledger_unmatched = []
for t, sym, amt in ledger_rows:
    lst = _sym_fills.get(sym, [])
    ts_ = [x[0] for x in lst]
    i = bisect.bisect_left(ts_, t - 3.0)
    if i < len(lst) and lst[i][0] <= t + 3.0:
        ledger_fee_by_rid[lst[i][1]] += amt
    else:
        ledger_unmatched.append((t, sym, amt))
_um = defaultdict(lambda: [0, 0.0])
for t, sym, amt in ledger_unmatched:
    if T_START <= t <= T_END:
        b = iso(int(t // 600) * 600)
        _um[b][0] += 1; _um[b][1] += amt
ledger_unmatched_summary = {"n_rows_in_window": int(sum(v[0] for v in _um.values())),
                            "usdt_in_window": round(float(sum(v[1] for v in _um.values())), 4),
                            "top_clusters_10min": [{"t": b, "n": v[0], "usdt": round(v[1], 4)} for b, v in sorted(_um.items(), key=lambda x: -x[1][1])[:12]],
                            "note": "配不上 fills 的账本佣金 = 08-21 12:16Z/08-05 12:18Z protective_flatten、λ执行探针(TAG/JASMY/DEXE/PARTI/RARE, 每锚+20min)、逐名止损出场等; 不属本书调仓成本"}

# ───────────────────────── 6. 逐行执行量 ─────────────────────────
maker_rows, topup_rows, resid_rows, flatten_rows, exit_rows = [], [], [], [], []
orders_fee_by_rid = defaultdict(float)
for o in orders:
    rid = o["rebalance_id"]; info = ANCHOR_INFO[rid]
    if o.get("fee_paid") is not None:
        orders_fee_by_rid[rid] += float(o["fee_paid"])
    ot = o["order_type"]; tr = o.get("terminal_reason")
    side = o.get("side"); s = 1.0 if side == "buy" else (-1.0 if side == "sell" else 0.0)
    fn = o.get("filled_notional"); px = o.get("avg_fill_px")
    if ot == "maker":
        if tr in ("filled", "partial_expired") and fn and px and s:
            ms, ma = o.get("mid_at_submit"), o.get("mid_at_anchor")
            maker_rows.append({"rid": rid, "sym": o["symbol"], "ts": info["ts"], "attempt": o.get("attempt_idx"),
                               "arm": o.get("placement_arm"), "side": side, "notional": abs(float(fn)),
                               "intended": abs(float(o.get("intended_full") or 0.0)),
                               "slip_sub": (s * (float(px) / float(ms) - 1.0) * 1e4) if ms else float("nan"),
                               "slip_anc": (s * (float(px) / float(ma) - 1.0) * 1e4) if ma else float("nan"),
                               "mid_anchor": ma, "spread_bps": o.get("spread_at_submit_bps"),
                               "t_first_fill": (float(o["first_fill_ts"]) - float(o["submit_ts"])) if (o.get("first_fill_ts") and o.get("submit_ts")) else float("nan")})
    elif ot == "topup_taker":
        if tr == "filled" and fn and px and s:
            ms, ma, lp = o.get("mid_at_submit"), o.get("mid_at_anchor"), o.get("intended_limit_px")
            topup_rows.append({"rid": rid, "sym": o["symbol"], "ts": info["ts"], "src": o.get("topup_source"),
                               "side": side, "notional": abs(float(fn)),
                               "drift_sub": (s * (float(px) / float(ms) - 1.0) * 1e4) if ms else float("nan"),
                               "drift_anc": (s * (float(px) / float(ma) - 1.0) * 1e4) if ma else float("nan"),
                               "drift_lim": (s * (float(px) / float(lp) - 1.0) * 1e4) if lp else float("nan"),
                               "mid_anchor": ma,
                               "lag_s": (float(o["submit_ts"]) - info["ts"]) if o.get("submit_ts") else float("nan")})
        else:
            res = o.get("intended_residual")
            if res is None:
                res = o.get("intended_notional")
            if res:
                resid_rows.append({"rid": rid, "sym": o["symbol"], "ts": info["ts"], "reason": tr, "src": o.get("topup_source"),
                                   "residual": float(res), "mid_anchor": o.get("mid_at_anchor")})
    elif ot == "protective_flatten":
        if fn and px and s and o.get("mid_at_submit") and info["in_window"]:
            flatten_rows.append({"rid": rid, "sym": o["symbol"], "notional": abs(float(fn)),
                                 "slip_sub": s * (float(px) / float(o["mid_at_submit"]) - 1.0) * 1e4})
    elif ot == "exit_only":
        if fn:
            exit_rows.append({"rid": rid, "sym": o["symbol"], "notional": abs(float(fn))})

# 未补单残差的机会成本: 到下一常规锚的方向性漂移
for r in resid_rows:
    nxt = next_reg.get(r["rid"])
    mid_next = (A_BY_RID.get(nxt, {}).get("mids") or {}).get(r["sym"]) if nxt else None
    ma = r["mid_anchor"]
    if mid_next and ma:
        s_res = 1.0 if r["residual"] > 0 else -1.0
        r["drift_next"] = s_res * (float(mid_next) / float(ma) - 1.0) * 1e4
    else:
        r["drift_next"] = float("nan")
# 同样给 maker 成交部分到下一锚的漂移(选择效应对照: 成交 vs 未成交)
for r in maker_rows:
    nxt = next_reg.get(r["rid"])
    mid_next = (A_BY_RID.get(nxt, {}).get("mids") or {}).get(r["sym"]) if nxt else None
    ma = r["mid_anchor"]
    s = 1.0 if r["side"] == "buy" else -1.0
    r["drift_next"] = (s * (float(mid_next) / float(ma) - 1.0) * 1e4) if (mid_next and ma) else float("nan")

MK = pd.DataFrame(maker_rows); TP = pd.DataFrame(topup_rows); RS = pd.DataFrame(resid_rows)
MO = pd.DataFrame(markout_rows, columns=["rid", "leg", "notional", "markout"])
for df in (MK, TP, RS, MO):
    df["class"] = df["rid"].map(lambda r: ANCHOR_INFO[r]["class"])
    df["period"] = df["rid"].map(lambda r: ANCHOR_INFO[r]["period"])
    df["in_window"] = df["rid"].map(lambda r: ANCHOR_INFO[r]["in_window"])
    df["regime"] = df["rid"].map(lambda r: ANCHOR_INFO[r]["regime"])


# ───────────────────────── 7. 聚合器 ─────────────────────────
def aggregate(rids, label):
    """对一组锚给出全口径分解 + 逐锚分布。"""
    rids = [r for r in rids]
    rs = set(rids)
    mk = MK[MK.rid.isin(rs)]; tp = TP[TP.rid.isin(rs)]; rsd = RS[RS.rid.isin(rs)]; mo = MO[MO.rid.isin(rs)]
    maker_n = float(mk.notional.sum()); taker_n = float(tp.notional.sum()); filled = maker_n + taker_n
    intended = float(sum(sum(intended_by_rid.get(r, {}).values()) for r in rids))
    unfilled = float(rsd.residual.abs().sum()) if len(rsd) else 0.0
    fee_ledger_matched = float(sum(ledger_fee_by_rid.get(r, 0.0) for r in rids))
    fee_fills_m = float(sum(fills_fee_by_rid_leg[r].get("maker", 0.0) for r in rids))
    fee_fills_t = float(sum(fills_fee_by_rid_leg[r].get("topup_taker", 0.0) for r in rids))
    fee_orders = float(sum(orders_fee_by_rid.get(r, 0.0) for r in rids))
    fills_n_m = float(sum(fills_notional_by_rid_leg[r].get("maker", 0.0) for r in rids))
    fills_n_t = float(sum(fills_notional_by_rid_leg[r].get("topup_taker", 0.0) for r in rids))
    # ★ 主源 = fills 逐笔佣金(本书自己的 trade_id); 账本配对值只作对账
    fee_m, fee_t = fee_fills_m, fee_fills_t
    fee_ledger = fee_fills_m + fee_fills_t
    slip_sub_usd = float((mk.slip_sub * mk.notional).sum() * 1e-4) if len(mk) else 0.0
    slip_anc_usd = float((mk.slip_anc * mk.notional).sum() * 1e-4) if len(mk) else 0.0
    drift_sub_usd = float((tp.drift_sub * tp.notional).sum() * 1e-4) if len(tp) else 0.0
    drift_anc_usd = float((tp.drift_anc * tp.notional).sum() * 1e-4) if len(tp) else 0.0
    opp_usd = float((rsd.drift_next * rsd.residual.abs()).sum() * 1e-4) if len(rsd) else 0.0
    opp_cov = float(rsd.residual.abs()[np.isfinite(rsd.drift_next)].sum()) if len(rsd) else 0.0

    def per(x, den):
        return round(x / den * 1e4, 4) if den > 0 else float("nan")

    comp = {
        "maker_fee": per(fee_m, filled), "maker_slip_vs_anchor": per(slip_anc_usd, filled), "maker_slip_vs_submit": per(slip_sub_usd, filled),
        "taker_fee": per(fee_t, filled), "taker_drift_vs_submit": per(drift_sub_usd, filled), "taker_drift_vs_anchor": per(drift_anc_usd, filled),
        "total_cash_vs_anchor": per(fee_ledger + slip_anc_usd + drift_anc_usd, filled),
        "total_cash_vs_submit": per(fee_ledger + slip_sub_usd + drift_sub_usd, filled),
        "opp_cost_unfilled_to_next_anchor": per(opp_usd, filled),
    }
    comp_int = {"total_cash_vs_anchor_per_intended": per(fee_ledger + slip_anc_usd + drift_anc_usd, intended),
                "opp_cost_unfilled_per_intended": per(opp_usd, intended),
                "total_incl_opp_per_intended": per(fee_ledger + slip_anc_usd + drift_anc_usd + opp_usd, intended)}
    within = {
        "maker_slip_vs_anchor_bps_of_maker": round(wmean(mk.slip_anc, mk.notional), 4) if len(mk) else None,
        "maker_slip_vs_submit_bps_of_maker": round(wmean(mk.slip_sub, mk.notional), 4) if len(mk) else None,
        "maker_fee_bps_of_maker": per(fee_m, maker_n),
        "taker_drift_vs_submit_bps_of_taker": round(wmean(tp.drift_sub, tp.notional), 4) if len(tp) else None,
        "taker_drift_vs_anchor_bps_of_taker": round(wmean(tp.drift_anc, tp.notional), 4) if len(tp) else None,
        "taker_drift_vs_limit_bps_of_taker": round(wmean(tp.drift_lim, tp.notional), 4) if len(tp) else None,
        "taker_fee_bps_of_taker": per(fee_t, taker_n),
        "taker_by_source": {src: {"notional": round(float(g.notional.sum()), 2), "drift_vs_submit": round(wmean(g.drift_sub, g.notional), 4),
                                  "drift_vs_anchor": round(wmean(g.drift_anc, g.notional), 4), "lag_s_median": round(float(g.lag_s.median()), 1) if len(g) else None}
                            for src, g in tp.groupby("src")} if len(tp) else {},
        "unfilled_by_reason": {rsn: {"notional": round(float(g.residual.abs().sum()), 2), "n": int(len(g)),
                                     "drift_next_bps": round(wmean(g.drift_next, g.residual.abs()), 4)} for rsn, g in rsd.groupby("reason")} if len(rsd) else {},
        "unfilled_drift_next_bps_of_unfilled(+=模型方向对=错过)": round(wmean(rsd.drift_next, rsd.residual.abs()), 4) if len(rsd) else None,
        "maker_filled_drift_next_bps_of_maker(同口径对照)": round(wmean(mk.drift_next, mk.notional), 4) if len(mk) else None,
        "maker_markout60_bps_of_covered": round(wmean(mo[mo.leg == "maker"].markout, mo[mo.leg == "maker"].notional), 4) if (mo.leg == "maker").any() else None,
        "taker_markout60_bps_of_covered": round(wmean(mo[mo.leg == "topup_taker"].markout, mo[mo.leg == "topup_taker"].notional), 4) if (mo.leg == "topup_taker").any() else None,
        "markout_coverage_notional": {"maker": round(float(mo[mo.leg == "maker"].notional.sum()), 2), "taker": round(float(mo[mo.leg == "topup_taker"].notional.sum()), 2)},
        "maker_first_fill_s_median": round(float(mk.t_first_fill.median()), 1) if len(mk) else None,
        "maker_spread_at_submit_bps_median": round(float(mk.spread_bps.median()), 3) if len(mk) else None,
    }
    # 逐锚分布(每锚: 现金全口径成本 / 成交额)
    per_anchor = []
    for r in rids:
        m = MK[MK.rid == r]; t = TP[TP.rid == r]
        fl = float(m.notional.sum() + t.notional.sum())
        if fl <= 0:
            continue
        fee_r = fills_fee_by_rid_leg[r].get("maker", 0.0) + fills_fee_by_rid_leg[r].get("topup_taker", 0.0)
        cash = fee_r + float((m.slip_anc * m.notional).sum() * 1e-4) + float((t.drift_anc * t.notional).sum() * 1e-4)
        cash_sub = fee_r + float((m.slip_sub * m.notional).sum() * 1e-4) + float((t.drift_sub * t.notional).sum() * 1e-4)
        rs_ = RS[RS.rid == r]
        opp_r = float((rs_.drift_next * rs_.residual.abs()).sum() * 1e-4) if len(rs_) else 0.0
        inten = sum(intended_by_rid.get(r, {}).values())
        per_anchor.append({"rid": r, "iso": ANCHOR_INFO[r]["iso"], "filled": round(fl, 2), "intended": round(inten, 2),
                           "taker_share": round(float(t.notional.sum()) / fl, 4),
                           "cash_bps_vs_anchor": round(cash / fl * 1e4, 4), "cash_bps_vs_submit": round(cash_sub / fl * 1e4, 4),
                           "fee_bps": round(fee_r / fl * 1e4, 4), "cash_usd": round(cash, 4), "cash_sub_usd": round(cash_sub, 4), "opp_usd": round(opp_r, 4),
                           "regime": ANCHOR_INFO[r]["regime"], "class": ANCHOR_INFO[r]["class"],
                           "turnover_ratio": ANCHOR_INFO[r]["intended_turnover_ratio"]})
    pa = pd.DataFrame(per_anchor)

    def ratio_boot(num, den, nb=3000, block=6, seed=17):
        num = np.asarray(num, float); den = np.asarray(den, float); L = len(num)
        if L < 4 or den.sum() <= 0:
            return [float("nan"), float("nan")]
        rng = np.random.default_rng(seed); k = int(np.ceil(L / block)); o = np.empty(nb)
        for q in range(nb):
            st = rng.integers(0, max(L - block, 1), size=k)
            ix = (st[:, None] + np.arange(block)[None, :]).ravel()[:L]; ix = ix[ix < L]
            o[q] = num[ix].sum() / max(den[ix].sum(), 1e-9) * 1e4
        return [round(float(np.percentile(o, 2.5)), 4), round(float(np.percentile(o, 97.5)), 4)]
    wboot = {}
    if len(pa):
        wboot = {"cash_vs_anchor_per_filled": ratio_boot(pa.cash_usd, pa.filled), "cash_vs_submit_per_filled": ratio_boot(pa.cash_sub_usd, pa.filled),
                 "cash_vs_anchor_per_intended": ratio_boot(pa.cash_usd, pa.intended), "opp_per_intended": ratio_boot(pa.opp_usd, pa.intended),
                 "cash_plus_opp_per_intended": ratio_boot(pa.cash_usd + pa.opp_usd, pa.intended)}
    out = {"label": label, "weighted_ratio_ci95_block6": wboot, "n_anchors": len(rids), "n_anchors_with_fills": int(len(pa)),
           "notional": {"intended": round(intended, 2), "filled_total": round(filled, 2), "maker_filled": round(maker_n, 2),
                        "taker_filled": round(taker_n, 2), "unfilled_residual": round(unfilled, 2),
                        "unfilled_with_next_mid": round(opp_cov, 2),
                        "maker_share_of_filled": round(maker_n / filled, 4) if filled else None,
                        "maker_fill_rate_of_intended": round(maker_n / intended, 4) if intended else None,
                        "taker_share_of_intended": round(taker_n / intended, 4) if intended else None,
                        "unfilled_share_of_intended": round(unfilled / intended, 4) if intended else None,
                        "identity_check_(maker+taker+unfilled)/intended": round((maker_n + taker_n + unfilled) / intended, 4) if intended else None},
           "fees_usdt": {"fills_maker": round(fee_fills_m, 4), "fills_taker": round(fee_fills_t, 4),
                         "fills_total(主源)": round(fee_fills_m + fee_fills_t, 4), "ledger_matched_total(对账)": round(fee_ledger_matched, 4),
                         "orders_fee_paid_total(对账)": round(fee_orders, 4),
                         "fills_notional_maker": round(fills_n_m, 2), "fills_notional_taker": round(fills_n_t, 2),
                         "ledger_matched_over_fills": round(fee_ledger_matched / (fee_fills_m + fee_fills_t), 4) if (fee_fills_m + fee_fills_t) > 0 else None,
                         "fee_rate_maker_bps(fills)": round(fee_fills_m / fills_n_m * 1e4, 4) if fills_n_m else None,
                         "fee_rate_taker_bps(fills)": round(fee_fills_t / fills_n_t * 1e4, 4) if fills_n_t else None,
                         "fee_rate_all_bps(fills/filled)": per(fee_ledger, filled)},
           "per_unit_filled_bps": comp, "per_unit_intended_bps": comp_int, "within_leg": within,
           "per_anchor_cash_bps_vs_anchor": stats(pa.cash_bps_vs_anchor) if len(pa) else {},
           "per_anchor_cash_bps_vs_submit": stats(pa.cash_bps_vs_submit) if len(pa) else {},
           "per_anchor_fee_bps": stats(pa.fee_bps) if len(pa) else {},
           "per_anchor_taker_share": stats(pa.taker_share) if len(pa) else {},
           "per_anchor_intended_turnover_ratio": stats(pa.turnover_ratio) if len(pa) else {},
           "notional_weighted_cash_bps_vs_anchor": comp["total_cash_vs_anchor"],
           "_per_anchor_rows": per_anchor}
    return out


win = [r for r, info in ANCHOR_INFO.items() if info["in_window"]]
G = {
    "inservice_normal": [r for r in win if ANCHOR_INFO[r]["class"] == "normal" and ANCHOR_INFO[r]["period"] == "inservice"],
    "pre_inservice_normal": [r for r in win if ANCHOR_INFO[r]["class"] == "normal" and ANCHOR_INFO[r]["period"] == "pre_inservice"],
    "window_normal_all": [r for r in win if ANCHOR_INFO[r]["class"] == "normal"],
    "rebuild": [r for r in win if ANCHOR_INFO[r]["class"] == "rebuild"],
    "resize": [r for r in win if ANCHOR_INFO[r]["class"] == "resize"],
    "inservice_normal_calm": [r for r in win if ANCHOR_INFO[r]["class"] == "normal" and ANCHOR_INFO[r]["period"] == "inservice" and ANCHOR_INFO[r]["regime"] == "calm"],
    "inservice_normal_vol_normal": [r for r in win if ANCHOR_INFO[r]["class"] == "normal" and ANCHOR_INFO[r]["period"] == "inservice" and ANCHOR_INFO[r]["regime"] == "normal"],
    "inservice_normal_bandit_era": [r for r in win if ANCHOR_INFO[r]["class"] == "normal" and ANCHOR_INFO[r]["ts"] >= T_BANDIT],
    "rebuild_0821_1600Z_only": [r for r in win if ANCHOR_INFO[r]["class"] == "rebuild" and ANCHOR_INFO[r]["iso"].startswith("2026-08-21T16")],
}
RESULTS = {k: aggregate(v, k) for k, v in G.items()}

# 逐锚行只保留一份(in-window 全部锚)
per_anchor_all = aggregate(win, "window_all")["_per_anchor_rows"]
for k in RESULTS:
    RESULTS[k].pop("_per_anchor_rows", None)

# ───────────────────────── 8. 按臂 / 按名 ─────────────────────────
# 按臂: 全部【已提交】attempt-1 maker 行(含零成交的 partial_expired), 成交率 = Σfilled/Σintended
sub_rows = []
for o in orders:
    if o["order_type"] != "maker" or o.get("attempt_idx") != 1 or o.get("submit_ts") is None:
        continue
    if o.get("terminal_reason") not in ("filled", "partial_expired"):
        continue
    info = ANCHOR_INFO[o["rebalance_id"]]
    if not (info["in_window"] and info["class"] == "normal" and info["period"] == "inservice"):
        continue
    fn = abs(float(o.get("filled_notional") or 0.0)); it = abs(float(o.get("intended_full") or 0.0))
    sub_rows.append({"arm": o.get("placement_arm"), "intended": it, "filled": fn, "any_fill": fn > 0,
                     "sym": o["symbol"], "rid": o["rebalance_id"], "ts": info["ts"]})
SB = pd.DataFrame(sub_rows)
arm_tab = {}
if len(SB):
    for arm, g in SB.groupby(SB.arm.fillna("none")):
        gm = MK[(MK.rid.isin(set(g.rid))) & (MK.attempt == 1) & (MK.arm.fillna("none") == arm)]
        arm_tab[str(arm)] = {"n_submitted": int(len(g)), "intended": round(float(g.intended.sum()), 2), "filled": round(float(g.filled.sum()), 2),
                             "fill_rate_notional": round(float(g.filled.sum() / g.intended.sum()), 4) if g.intended.sum() else None,
                             "fill_rate_count(any_fill)": round(float(g.any_fill.mean()), 4),
                             "slip_vs_anchor_of_filled": round(wmean(gm.slip_anc, gm.notional), 4) if len(gm) else None,
                             "slip_vs_submit_of_filled": round(wmean(gm.slip_sub, gm.notional), 4) if len(gm) else None,
                             "drift_next_of_filled": round(wmean(gm.drift_next, gm.notional), 4) if len(gm) else None,
                             "note": "仅 ε-赌博机上线(08-12 04:00Z)后行有 arm; none=上线前"}

per_name = []
ins_rids = set(G["inservice_normal"])
mk_n = MK[MK.rid.isin(ins_rids)]; tp_n = TP[TP.rid.isin(ins_rids)]; rs_n = RS[RS.rid.isin(ins_rids)]
inten_sym = defaultdict(float)
for r in ins_rids:
    for s_, v in intended_by_rid.get(r, {}).items():
        inten_sym[s_] += v
for sym in sorted(inten_sym):
    m = mk_n[mk_n.sym == sym]; t = tp_n[tp_n.sym == sym]; u = rs_n[rs_n.sym == sym]
    mn = float(m.notional.sum()); tn = float(t.notional.sum()); un = float(u.residual.abs().sum()) if len(u) else 0.0
    inten = inten_sym[sym]
    if inten < 1.0:
        continue
    cash = float((m.slip_anc * m.notional).sum() * 1e-4 + (t.drift_anc * t.notional).sum() * 1e-4)
    per_name.append({"symbol": sym, "intended": round(inten, 2), "maker_fill_rate": round(mn / inten, 4), "taker_share": round(tn / inten, 4),
                     "unfilled_share": round(un / inten, 4), "maker_slip_vs_anchor": round(wmean(m.slip_anc, m.notional), 4) if mn else None,
                     "taker_drift_vs_submit": round(wmean(t.drift_sub, t.notional), 4) if tn else None,
                     "cash_ex_fee_bps_per_filled": round(cash / (mn + tn) * 1e4, 4) if (mn + tn) else None,
                     "n_anchors": int(m.rid.nunique())})
PN = pd.DataFrame(per_name)

# ───────────────────────── 9. 旧假设对照 ─────────────────────────
main = RESULTS["inservice_normal"]
meas = main["per_unit_filled_bps"]["total_cash_vs_anchor"]
meas_ci = main["per_anchor_cash_bps_vs_anchor"].get("ci95_mean_block6")
OLD = {
    "turnover_frontier_2026-07-26(frontier_sweep.py)": {"cost_per_unit_traded_bps": 4.5, "note": "主口径 VIP0 最坏: 费+半价差+tick逆选择; 引擎默认 1.9; 交叉点 λ.25@6.93 / λ.5@8.49(每单位成交额, 单向 Σ|Δw|)"},
    "king_cadence_8h_proposal_2026-08-09(cad8.py)": {"cost_per_unit_traded_bps": 6.23, "note": "脚本 np_ = p − t·2·c, c∈{3.115,5.8} ⇒ 有效每单位换手 6.23 / 11.6(3.115 被当作'每边'再×2)"},
    "deepsmooth/neutral_band/cond_stop/w2_live_replay(4.137)": {"cost_per_unit_traded_bps": 4.137, "note": "08-10 实测混合 maker −0.254(75.1%)+topup +17.39(24.9%); 在役离线基线夏普 1.46 建立于此; C2=6.23 次口径"},
    "cost_rebaseline_2026-08-09(RESULT_cost_postswap)": {"cost_per_unit_traded_bps": 3.115, "note": "费 2.235 + edge −0.879, 1447 笔 08-05 20:00Z 起; 只含成交, 补单 from_partial +34.6"},
}
comparison = {"measured_inservice_normal_cash_per_unit_filled_vs_anchor": meas,
              "measured_ci95_weighted_ratio": main["weighted_ratio_ci95_block6"],
              "measured_ci95_anchor_mean(等权锚)": meas_ci,
              "measured_per_unit_intended_incl_opp": main["per_unit_intended_bps"],
              "old_assumptions": OLD,
              "relative_diff_vs_old": {k: (round(meas / v["cost_per_unit_traded_bps"] - 1.0, 4) if np.isfinite(meas) else None) for k, v in OLD.items()}}

# ───────────────────────── 10. 落盘 ─────────────────────────
out = {
    "meta": {"created_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "session": "6737834a-T1",
             "window": {"start": iso(T_START + 600), "end": iso(T_END), "inservice_from": iso(T_INSERVICE + 600), "bandit_from": iso(T_BANDIT + 600)},
             "fills_rows_raw": len(fills_raw), "fills_unique_trade_id": len(fills),
             "bnb_px_source": "anchors.jsonl mid_at_anchor_vector[BNBUSDT] 最近锚(≤t)", "bnb_px_fallback": BNB_FALLBACK,
             "ledger_unmatched_commission": ledger_unmatched_summary},
    "inputs_sha256": inputs,
    "anchors": {r: v for r, v in ANCHOR_INFO.items() if v["in_window"]},
    "anchor_class_counts": dict(pd.Series([v["class"] for v in ANCHOR_INFO.values() if v["in_window"]]).value_counts()),
    "results": RESULTS,
    "per_anchor_rows_window": per_anchor_all,
    "placement_arm_inservice_attempt1": arm_tab,
    "per_name_inservice_normal": PN.sort_values("intended", ascending=False).to_dict("records") if len(PN) else [],
    "flatten": {"n_rows": len(flatten_rows), "notional": round(float(sum(r["notional"] for r in flatten_rows)), 2),
                "slip_vs_submit_bps": round(wmean([r["slip_sub"] for r in flatten_rows], [r["notional"] for r in flatten_rows]), 4) if flatten_rows else None,
                "note": "平仓费在账本未配对簇里(08-21 12:10Z 簇 ≈12.9U, 08-05 12:10Z 簇 ≈2.0U), 见 meta.ledger_unmatched_commission"},
    "comparison_with_old_assumptions": comparison,
}
os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump(out, open(OUT, "w"), indent=1, ensure_ascii=False, default=lambda x: None if (isinstance(x, float) and not np.isfinite(x)) else (float(x) if isinstance(x, (np.floating,)) else (int(x) if isinstance(x, (np.integer,)) else str(x))))

# ───────────────────────── 11. 摘要打印 ─────────────────────────
print("=== anchor classes (in window) ===", out["anchor_class_counts"])
for r, v in ANCHOR_INFO.items():
    if v["in_window"] and v["class"] != "normal":
        print("  ", v["iso"], v["class"], "ratio", v["intended_turnover_ratio"], "regime", v["regime"])
for k in ("inservice_normal", "pre_inservice_normal", "window_normal_all", "rebuild", "resize", "rebuild_0821_1600Z_only",
          "inservice_normal_calm", "inservice_normal_vol_normal", "inservice_normal_bandit_era"):
    R = RESULTS[k]
    print(f"\n=== {k}: anchors {R['n_anchors']} ===")
    print(" notional:", json.dumps(R["notional"]))
    print(" fees:", json.dumps(R["fees_usdt"]))
    print(" per_unit_filled:", json.dumps(R["per_unit_filled_bps"]))
    print(" per_unit_intended:", json.dumps(R["per_unit_intended_bps"]))
    print(" within_leg:", json.dumps(R["within_leg"], ensure_ascii=False))
    print(" weighted ratio CI:", json.dumps(R["weighted_ratio_ci95_block6"]))
    print(" per_anchor cash vs anchor:", json.dumps(R["per_anchor_cash_bps_vs_anchor"]))
    print(" per_anchor cash vs submit:", json.dumps(R["per_anchor_cash_bps_vs_submit"]))
    print(" per_anchor turnover ratio:", json.dumps(R["per_anchor_intended_turnover_ratio"]))
print("\n=== placement arm (inservice attempt-1, all submitted) ===", json.dumps(arm_tab, ensure_ascii=False))
print("\n=== comparison ===", json.dumps(comparison, ensure_ascii=False, indent=1)[:3000])
print("\n=== flatten ===", json.dumps(out["flatten"]))
print("SAVED", OUT)
