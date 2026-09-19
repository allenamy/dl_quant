#!/usr/bin/env python3
"""实盘 g · 完整人口 v3(复审 R5B-06 / R5B-07 修复)。只读。

v2(live_g_population_v2.py de20d114)被复审指出:
  R5B-06 I 分母把窗首 target_gross 沿用到窗末 —— 约 8h 的长窗里中途会改目标 / 停机 / 重建, 分母不唯一;
         反例: 两段各 4h, gross 100 / 200, 净额 1 / 2(各 100 bps), 合并后沿用首段 gross 算成 150 bps。
         比较器写死 W=143 而实盘跨度 ≈145.016 个 4h; 历史底座(研究回放)还有成员外持仓不计价缺陷 ⇒ 百分位比较不再做。
         「意图 gross 作分母 = 计入机会成本」这句不成立: 分母本身测不出机会成本(需反事实)。I 的正确读法 = 每单位意图预算的回报。
  R5B-07 I / N 复用了 H 的 f(r) > 0 筛选(把 target_gross 改成 0 就能把一个亏损窗移出主人口, 回归门仍过);
         新增依赖(anchors / readback / daily_nav)只记路径字符串, 没有封存用到的行; target 可无限沿用陈旧锚; 同一 read_ts/symbol 的不同值后写覆盖。

v3:
  1. 封存: `seal` 子命令只读生产账本, 把本计算【实际用到的每一行】写成一份审计副本 JSON(带 sha256); `compute` 子命令只读这份副本,
     不碰生产目录 —— 审计方可在副本上逐位复跑。
  2. 读回冲突: 同一 (read_ts, symbol) 出现不同的 venue_position_notional ⇒ 具名拒绝(REFUSED_READBACK_CONFLICT), 不后写覆盖。
  3. 意图分母按时钟分段: 窗 [t0, t1) 内每个执行器锚记录(anchor_ts)都是一个分段点; 每段的意图 gross = 该段开始时【生效】的
     target_gross(最后一条 anchor_ts ≤ 段起点 + 120 s 的记录)× 段长 / 4h。生效记录早于段起点超过 MAX_TARGET_AGE_S(= 8h + 30 min,
     即最多沿用一个漏掉的锚: 执行器 HOLD 时书确实维持上一个目标)⇒ 具名 STALE_TARGET, 主指标拒算。
  4. 非法分母不缩人口: I / N 任一窗分母非有限或 ≤ 0 ⇒ 该分母的主指标拒算并具名(REFUSED_INVALID_DENOMINATOR), 不把窗移到旁列。
     H(梯形持仓)区分「快照缺失 = 未知」与「两端为 0 = 真零」: 未知 ⇒ H 主指标拒算; 真零窗单列其现金(H 对它无定义)。
  5. 不做与研究回放的百分位比较(R5B-06); 实盘与模拟的同窗比较留给「对象 A × 模拟器 v3」。
usage:
  live_g_population_v3.py seal <CASH_IDENTITY_USD.json> <seal_out.json> [from_utc]
  live_g_population_v3.py compute <seal.json> <out.json>"""
import bisect, calendar, collections, hashlib, json, math, os, sys, time

LED = os.path.expanduser("~/dl_quant_live/state/live/pilot_log")
U = lambda t: time.strftime("%m-%d %H:%M:%SZ", time.gmtime(float(t)))
H4 = 14400.0
ANCHOR_TOL_S = 120.0
MAX_TARGET_AGE_S = 8 * 3600 + 1800
SNAP_TOL_S = 60.0
COMPS = ("net", "price_trade", "funding", "fee")


def sha_bytes(b): return hashlib.sha256(b).hexdigest()
def sha_file(p): return sha_bytes(open(p, "rb").read())
def canon(o): return json.dumps(o, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


class Refused(Exception):
    pass


def fin(x):
    return isinstance(x, (int, float)) and math.isfinite(float(x))


# ───────────────────────── seal (reads production ledger, read-only) ─────────────────────────
def seal(rec_p, out_p, t_from):
    rec = json.load(open(rec_p))
    days = sorted(d for d in os.listdir(LED) if d.startswith("2026"))
    nav_rows, rb_rows, anc_rows = [], [], []
    for d in days:
        for fn, sink in (("daily_nav.jsonl", nav_rows), ("position_readback.jsonl", rb_rows), ("anchors.jsonl", anc_rows)):
            p = f"{LED}/{d}/{fn}"
            if os.path.isfile(p):
                for i, l in enumerate(open(p)):
                    if l.strip():
                        sink.append({"file": f"{d}/{fn}", "line": i + 1, "row": json.loads(l)})
    nav = {}
    for x in nav_rows:
        r = x["row"]
        if r.get("mode") in (None, "LIVE"): nav.setdefault(U(r["nav_ts"]), []).append(x)
    wins = [w for w in rec["windows_4h"]]
    used_nav, used_rb, snaps_needed = [], [], set()
    rb_by_ts = collections.defaultdict(list)
    for x in rb_rows: rb_by_ts[float(x["row"]["read_ts"])].append(x)
    rb_ts = sorted(rb_by_ts)
    keep_w = []
    for w in wins:
        if "terms" not in w: raise Refused(f"window {w['from']} has no terms")
        a, b = nav.get(w["from"]), nav.get(w["to"])
        if not a or not b: raise Refused(f"window {w['from']} not mapped to a NAV row")
        if len({canon(x['row']) for x in a}) > 1 or len({canon(x['row']) for x in b}) > 1:
            raise Refused(f"REFUSED_NAV_CONFLICT at {w['from']} / {w['to']}")
        t0, t1 = float(a[0]["row"]["nav_ts"]), float(b[0]["row"]["nav_ts"])
        if t0 < t_from: continue
        keep_w.append(w); used_nav += [a[0], b[0]]
        for t in (t0, t1):
            j = bisect.bisect_left(rb_ts, t); c = [s for s in rb_ts[max(0, j - 2):j + 2] if abs(s - t) <= SNAP_TOL_S]
            if c:
                k = min(c, key=lambda s: (abs(s - t), s)); snaps_needed.add(k)
    for k in sorted(snaps_needed): used_rb += rb_by_ts[k]
    tmin = min(float(x["row"]["nav_ts"]) for x in used_nav) - MAX_TARGET_AGE_S - 3600
    tmax = max(float(x["row"]["nav_ts"]) for x in used_nav)
    used_anc = [x for x in anc_rows if tmin <= float(x["row"]["anchor_ts"]) <= tmax]
    slim = lambda xs, keys: [{"file": x["file"], "line": x["line"], "row": {k: x["row"].get(k) for k in keys}} for x in xs]
    doc = {"seal": "LIVE_LEDGER_SEAL_for_live_g_v3", "device_sha256": sha_file(os.path.abspath(__file__)),
           "sealed_utc": time.strftime("%FT%TZ", time.gmtime()), "from_utc": time.strftime("%FT%TZ", time.gmtime(t_from)),
           "cash_identity": {"file": os.path.basename(rec_p), "sha256": sha_file(rec_p)},
           "windows_4h": keep_w,
           "daily_nav_rows": slim(used_nav, ("nav_ts", "mode", "nav", "external_flow_usdt")),
           "position_readback_rows": slim(used_rb, ("read_ts", "symbol", "venue_position_notional", "source")),
           "anchor_rows": slim(used_anc, ("anchor_ts", "target_gross", "realized_gross"))}
    body = canon(doc); doc_sha = sha_bytes(body)
    with open(out_p + ".part", "wb") as fh: fh.write(body)
    os.replace(out_p + ".part", out_p)
    if sha_file(out_p) != doc_sha: raise Refused("seal write verification failed")
    print(f"sealed {len(keep_w)} windows · nav rows {len(used_nav)} · readback rows {len(used_rb)} · anchor rows {len(used_anc)} · sha256 {doc_sha}")


# ───────────────────────── compute (reads the seal only) ─────────────────────────
def build_rows(S):
    nav_ts = {U(x["row"]["nav_ts"]): float(x["row"]["nav_ts"]) for x in S["daily_nav_rows"]}
    rb = collections.defaultdict(dict)
    for x in S["position_readback_rows"]:
        r = x["row"]; k = float(r["read_ts"]); v = r["venue_position_notional"]
        if not fin(v): raise Refused(f"REFUSED_NONFINITE_READBACK {r['symbol']} @ {U(k)}")
        if r["symbol"] in rb[k] and rb[k][r["symbol"]] != abs(float(v)):
            raise Refused(f"REFUSED_READBACK_CONFLICT {r['symbol']} @ {U(k)}: {rb[k][r['symbol']]} vs {abs(float(v))}")
        rb[k][r["symbol"]] = abs(float(v))
    snaps = sorted(rb)
    anc = []
    for x in S["anchor_rows"]:
        r = x["row"]
        if not fin(r.get("anchor_ts")): raise Refused("REFUSED_NONFINITE_ANCHOR_TS")
        anc.append((float(r["anchor_ts"]), r.get("target_gross")))
    anc.sort(); at = [a for a, _ in anc]

    def gross_at(ts):
        j = bisect.bisect_left(snaps, ts); c = [s for s in snaps[max(0, j - 2):j + 2] if abs(s - ts) <= SNAP_TOL_S]
        if not c: return None                                          # 未知(不是 0)
        return sum(rb[min(c, key=lambda k: (abs(k - ts), k))].values())

    def target_in_effect(ts):
        j = bisect.bisect_right(at, ts + ANCHOR_TOL_S) - 1
        if j < 0: return None, None, "NO_TARGET_RECORD"
        a, tg = anc[j]
        if ts - a > MAX_TARGET_AGE_S: return tg, a, "STALE_TARGET"
        return tg, a, None

    rows = []
    for w in S["windows_4h"]:
        t0, t1 = nav_ts.get(w["from"]), nav_ts.get(w["to"])
        if t0 is None or t1 is None: raise Refused(f"window {w['from']} not in seal")
        if not (fin(t0) and fin(t1) and t1 > t0): raise Refused(f"REFUSED_WINDOW_TIME {w['from']}")
        T = w["terms"]; fl = T["flows"]
        for v in [T["mtm_and_trade_cash"], *fl.values(), *T["N"], *T["p"], *T["b"]]:
            if not fin(v): raise Refused(f"REFUSED_NONFINITE_TERM in window {w['from']}")
        bnb_px = T["b"][1] / 0.95
        fund = fl.get("FUNDING_FEE|USDT", 0.0)
        fee = -(fl.get("COMMISSION|USDT", 0.0) + fl.get("COMMISSION|BNB", 0.0) * bnb_px)
        xfer = fl.get("TRANSFER|USDT", 0.0) + fl.get("TRANSFER|BNB", 0.0) * bnb_px
        N0u = T["N"][0] / T["p"][0]
        # 意图分母: 在窗内每个锚记录处分段
        cuts = [t0] + [a for a in at if t0 + ANCHOR_TOL_S < a < t1 - ANCHOR_TOL_S] + [t1]
        segs, flags = [], []
        for s0, s1 in zip(cuts, cuts[1:]):
            tg, a, flag = target_in_effect(s0)
            segs.append({"from": U(s0), "to": U(s1), "hours": round((s1 - s0) / 3600, 4), "target_gross": tg, "target_anchor": U(a) if a else None})
            if flag: flags.append(f"{flag}@{U(s0)}")
            if not fin(tg) or tg <= 0: flags.append(f"INVALID_TARGET_GROSS@{U(s0)}={tg}")
        D_I = sum((s["target_gross"] if fin(s["target_gross"]) else float("nan")) * s["hours"] * 3600 / H4 for s in segs)
        g0, g1 = gross_at(t0), gross_at(t1)
        rows.append({"from": w["from"], "to": w["to"], "t0": t0, "t1": t1, "u": (t1 - t0) / H4, "n_segments": len(segs), "segments": segs,
                     "intent_flags": flags, "D_I": D_I, "gross0": g0, "gross1": g1,
                     "D_H": (None if g0 is None or g1 is None else 0.5 * (g0 + g1) * (t1 - t0) / H4),
                     "D_N": N0u * (t1 - t0) / H4, "nav0_usdt": N0u, "transfer_usdt": xfer,
                     "price_trade": T["mtm_and_trade_cash"], "funding": fund, "fee": fee, "net": T["mtm_and_trade_cash"] + fund - fee})
    for a, b in zip(rows, rows[1:]):
        if abs(a["t1"] - b["t0"]) > 1e-6: raise Refused(f"REFUSED_NONCONTIGUOUS at {a['to']}")
    return rows


def stats(rows, key):
    """Main metric over the FULL population. Any invalid denominator ⇒ refused with a name (never a shrunk population)."""
    bad = [r["from"] for r in rows if not (r[key] is not None and fin(r[key]) and r[key] > 0)]
    if key == "D_I":
        bad += [r["from"] for r in rows if r["intent_flags"] and r["from"] not in bad]
    if bad:
        return {"verdict": "REFUSED_INVALID_DENOMINATOR", "n_windows": len(rows), "n_invalid": len(bad), "invalid_windows": bad[:20]}
    den = sum(r[key] for r in rows); u = sum(r["u"] for r in rows)
    return {"verdict": "OK", "n_windows": len(rows), "total_4h_units": round(u, 6),
            "ratio_of_sums_bps_per_4h": {c: round(sum(r[c] for r in rows) / den * 1e4, 4) for c in COMPS},
            "time_weighted_mean_bps_per_4h": {c: round(sum(r["u"] * r[c] / r[key] for r in rows) / u * 1e4, 4) for c in COMPS}}


def stats_H(rows):
    unknown = [r["from"] for r in rows if r["D_H"] is None]
    if unknown:
        return {"verdict": "REFUSED_UNKNOWN_SNAPSHOT", "n_unknown": len(unknown), "unknown_windows": unknown[:20]}
    zero = [r for r in rows if r["D_H"] == 0]
    pos = [r for r in rows if r["D_H"] > 0]
    den = sum(r["D_H"] for r in pos); u = sum(r["u"] for r in pos)
    return {"verdict": "OK (defined only where held exposure > 0; true-zero windows listed separately)",
            "n_windows_positive": len(pos), "n_windows_true_zero": len(zero),
            "true_zero_cash_usdt": {c: round(sum(r[c] for r in zero), 6) for c in COMPS},
            "ratio_of_sums_bps_per_4h": {c: round(sum(r[c] for r in pos) / den * 1e4, 4) for c in COMPS},
            "time_weighted_mean_bps_per_4h": {c: round(sum(r["u"] * r[c] / r["D_H"] for r in pos) / u * 1e4, 4) for c in COMPS},
            "note": "trapezoid of end snapshots: cannot see intra-window round trips (R5B-06)"}


def compute(seal_p, out_p):
    raw = open(seal_p, "rb").read(); S = json.loads(raw)
    rows = build_rows(S)
    doc = {"receipt": "LIVE_G_POPULATION_v3", "device_sha256": sha_file(os.path.abspath(__file__)),
           "seal": {"file": os.path.basename(seal_p), "sha256": sha_bytes(raw)}, "utc": time.strftime("%FT%TZ", time.gmtime()),
           "from": rows[0]["from"], "to": rows[-1]["to"], "n_windows": len(rows), "total_4h_units": round(sum(r["u"] for r in rows), 6),
           "cash_total_usdt": {c: round(sum(r[c] for r in rows), 6) for c in COMPS},
           "I_intended_budget_piecewise": {**stats(rows, "D_I"), "reading": "return per unit of intended gross budget over time (budget utilisation); NOT an opportunity-cost measurement"},
           "N_nav": {**stats(rows, "D_N"), "reading": "return per unit of start-of-window NAV (USDT), time-scaled"},
           "H_held_trapezoid": stats_H(rows),
           "comparison_to_replay": "not computed: the research replay distribution has the out-of-member unpriced-position defect and a fixed 143-anchor span (R5B-06); same-window comparison deferred to object A × simulator v3",
           "long_windows": [{k: r[k] for k in ("from", "to", "u", "n_segments", "segments", "net")} for r in rows if r["n_segments"] > 2 or abs(r["u"] - 1) > 0.05],
           "windows": rows}
    with open(out_p + ".part", "w") as fh: json.dump(doc, fh, indent=1)
    os.replace(out_p + ".part", out_p)
    print(json.dumps({k: doc[k] for k in ("from", "to", "n_windows", "total_4h_units", "cash_total_usdt", "I_intended_budget_piecewise", "N_nav", "H_held_trapezoid")}, indent=1, ensure_ascii=False))
    for r in doc["long_windows"]: print("long/segmented window", r["from"], "→", r["to"], f"u={r['u']:.3f} segments={r['n_segments']}", [(s['from'], s['hours'], s['target_gross']) for s in r["segments"]])


if __name__ == "__main__":
    if len(sys.argv) >= 4 and sys.argv[1] == "seal":
        t_from = calendar.timegm(time.strptime(sys.argv[4] if len(sys.argv) > 4 else "2026-08-26T00:00:00Z", "%Y-%m-%dT%H:%M:%SZ"))
        try: seal(sys.argv[2], sys.argv[3], t_from)
        except Refused as e: print(f"REFUSED: {e}"); sys.exit(2)
    elif len(sys.argv) == 4 and sys.argv[1] == "compute":
        try: compute(sys.argv[2], sys.argv[3])
        except Refused as e: print(f"REFUSED: {e}"); sys.exit(2)
    else:
        print(__doc__); sys.exit(64)
