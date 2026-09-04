"""READ-ONLY structural dump of executor logs + producer state, 2026-08-25 .. now. No secrets printed."""
import os, json, glob, time, statistics
import numpy as np
PL = "/Users/haosiyu/dl_quant_live/state/live/pilot_log"; WS = "/Users/haosiyu/wide_shadow"; RD = "/Users/haosiyu/regime_dash"
def fmt(t): return time.strftime("%m-%d %H:%M:%SZ", time.gmtime(float(t)))
days = sorted(d for d in os.listdir(PL) if d.isdigit() and d >= "20260825")
def rows(d, name):
    p = f"{PL}/{d}/{name}"
    if not os.path.exists(p): return []
    out = []
    for ln in open(p):
        ln = ln.strip()
        if not ln: continue
        try: out.append(json.loads(ln))
        except Exception as e: out.append({"_bad": str(e)[:40]})
    return out

print("=== anchors.jsonl ===")
print("day | anchor_ts(actual) | nominal | off_s | realized_gross | rg_source | n_mid | halted | ext.ok | ext.reason | ext.path | ext.nominal_ts")
for d in days:
    for r in rows(d, "anchors.jsonl"):
        if "_bad" in r: print(d, "BAD ROW", r); continue
        at = float(r["anchor_ts"]); N = int(at // 14400 * 14400)
        mv = r.get("mid_at_anchor_vector"); mv = json.loads(mv) if isinstance(mv, str) else (mv or {})
        eb = r.get("external_book") or {}
        print(f"{d} | {fmt(at)} | {fmt(N)} | {at-N:7.1f} | {float(r.get('realized_gross') or 0):9.1f} | {r.get('realized_gross_source')} | {len(mv)} | {r.get('opening_halted')} | {eb.get('ok')} | {eb.get('reason')} | {os.path.basename(str(eb.get('path')))} | {eb.get('nominal_ts')}")

print("\n=== position_readback.jsonl (grouped by anchor_ts, source) ===")
print("day | anchor_ts | source | n_rows | n_nonzero_qty | sum|notional| | read_ts-anchor_ts (min..max)")
for d in days:
    g = {}
    for r in rows(d, "position_readback.jsonl"):
        if "_bad" in r: print(d, "BAD ROW", r); continue
        k = (float(r["anchor_ts"]), r.get("source"))
        g.setdefault(k, []).append(r)
    for (at, src), rs in sorted(g.items()):
        nz = sum(1 for r in rs if float(r.get("venue_position_qty") or 0) != 0)
        sn = sum(abs(float(r.get("venue_position_notional") or 0)) for r in rs)
        dl = [float(r.get("read_ts") or at) - at for r in rs]
        print(f"{d} | {fmt(at)} | {src} | {len(rs)} | {nz} | {sn:9.1f} | {min(dl):.1f}..{max(dl):.1f}")

print("\n=== daily_nav.jsonl (ALL rows) ===")
print("day | nav_ts | nav | prev_day | prev_nav | eq_delta_since_prev | ext_flow | realised_pnl(since00Z) | unrealised | wallet | target_gross")
for d in days:
    for r in rows(d, "daily_nav.jsonl"):
        if "_bad" in r: print(d, "BAD ROW", r); continue
        print(f"{d} | {fmt(r['nav_ts'])} | {float(r['nav']):9.2f} | {r.get('prev_day')} | {float(r.get('prev_nav') or 0):9.2f} | {float(r.get('equity_delta_since_prev') or 0):+9.2f} | {float(r.get('external_flow_usdt') or 0):9.2f} | {float(r.get('realised_pnl') or 0):+9.2f} | {float(r.get('unrealised_pnl') or 0):+9.2f} | {float(r.get('wallet_balance') or 0):9.2f} | {r.get('target_gross')}")

print("\n=== fills.jsonl: per anchor fill-time delays ===")
print("day | anchor_ts(actual) | nominal | n_fills | n_maker | first_fill-anchor_ts | median(fill-anchor_ts) | notional-wtd median | first_fill-nominal | median-nominal | last_fill-nominal | sum_notional")
allmed_act = []; allfirst_act = []; allmed_nom = []; allfirst_nom = []; allwmed_nom = []
for d in days:
    g = {}
    for r in rows(d, "fills.jsonl"):
        if "_bad" in r: print(d, "BAD ROW", r); continue
        g.setdefault(float(r["anchor_ts"]), []).append(r)
    for at, rs in sorted(g.items()):
        N = int(at // 14400 * 14400)
        ft = np.array([float(r["fill_ts"]) for r in rs]); nt = np.array([abs(float(r.get("fill_notional") or 0)) for r in rs])
        o = np.argsort(ft); cw = np.cumsum(nt[o]) / nt.sum(); wmed = ft[o][np.searchsorted(cw, 0.5)]
        nm = sum(1 for r in rs if r.get("order_type") == "maker")
        print(f"{d} | {fmt(at)} | {fmt(N)} | {len(rs)} | {nm} | {ft.min()-at:7.1f} | {np.median(ft)-at:7.1f} | {wmed-at:7.1f} | {ft.min()-N:7.1f} | {np.median(ft)-N:7.1f} | {ft.max()-N:7.1f} | {nt.sum():9.1f}")
        allmed_act.append(np.median(ft) - at); allfirst_act.append(ft.min() - at); allmed_nom.append(np.median(ft) - N); allfirst_nom.append(ft.min() - N); allwmed_nom.append(wmed - N)
print(f"ACROSS ANCHORS: median(first_fill-anchor_ts)={np.median(allfirst_act):.1f}s  median(median fill-anchor_ts)={np.median(allmed_act):.1f}s  median(first_fill-nominal)={np.median(allfirst_nom):.1f}s  median(median fill-nominal)={np.median(allmed_nom):.1f}s  median(notional-wtd median fill - nominal)={np.median(allwmed_nom):.1f}s  n={len(allmed_act)}")

print("\n=== funding.jsonl: per day ===")
print("day | n_rows | n_distinct_settlement_ts | settlement_ts set (hours) | sum funding_paid | n dup (settlement_ts,symbol)")
for d in days:
    rs = [r for r in rows(d, "funding.jsonl") if "_bad" not in r]
    st = sorted(set(float(r["settlement_ts"]) for r in rs))
    keys = [(float(r["settlement_ts"]), r["symbol"]) for r in rs]
    ndup = len(keys) - len(set(keys))
    hrs = sorted(set(time.strftime("%m-%d %H", time.gmtime(t)) for t in st))
    print(f"{d} | {len(rs)} | {len(st)} | {hrs[0] if hrs else None}..{hrs[-1] if hrs else None} n={len(hrs)} | {sum(float(r['funding_paid']) for r in rs):+9.3f} | {ndup}")

print("\n=== target_live files 2026-08-25.. ===")
fs = sorted(glob.glob(f"{WS}/state/target_live/*.json"))
for p in fs:
    b = os.path.basename(p)
    try: t = int(b.split(".")[0])
    except: continue
    if t < 1787616000: continue
    doc = json.load(open(p)); w = doc.get("weights", {}); g = sum(abs(float(v)) for v in w.values())
    print(f"{fmt(t)} | {b} | n_w={len(w)} | sum|w|={g:.4f} | gross_norm={doc.get('gross_norm')} | keys={sorted(k for k in doc.keys() if k!='weights')}")

print("\n=== regime_dash.jsonl: sleeve_prev_interval_usdt totals (interval prevA->A, labelled by A) ===")
print("A(anchor_ts) | price_sum | carry_sum | total | n_buckets")
seen = {}
for ln in open(f"{RD}/regime_dash.jsonl"):
    try: r = json.loads(ln)
    except: continue
    a = int(r.get("anchor_ts") or 0)
    if a < 1787702400: continue
    sl = r.get("sleeve_prev_interval_usdt")
    seen[a] = sl   # last row per anchor wins
for a in sorted(seen):
    sl = seen[a]
    if isinstance(sl, dict) and "error" not in sl and sl:
        pr = sum(v["price"] for v in sl.values()); ca = sum(v["carry"] for v in sl.values())
        print(f"{fmt(a)} | {pr:+9.2f} | {ca:+8.2f} | {pr+ca:+9.2f} | {len(sl)}")
    else:
        print(f"{fmt(a)} | sleeve={sl}")

print("\n=== beta_alpha.jsonl (ALL rows) ===")
for ln in open(f"{RD}/beta_alpha.jsonl"):
    r = json.loads(ln); print(r)
