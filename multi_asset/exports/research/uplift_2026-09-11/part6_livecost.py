#!/usr/bin/env python3
"""Part 6: the REALIZED live cost of turnover, from the executor's own fills ledger, and the
turnover<->tail exchange rate expressed in the units the decision is actually made in."""
import os, json, glob, collections
import numpy as np
PL = "/Users/haosiyu/dl_quant_live/state/live/pilot_log"
days = sorted(os.path.basename(d) for d in glob.glob(f"{PL}/2026*"))
print("days", days[0], "..", days[-1], "n=", len(days))

per_day = collections.OrderedDict()
seen = collections.defaultdict(set)   # E-0909-H: dedupe by trade_id per day
for d in days:
    f = f"{PL}/{d}/fills.jsonl"
    notion = 0.0; comm = 0.0; n = 0; mk = 0; slip_num = 0.0; slip_den = 0.0
    if os.path.exists(f):
        for ln in open(f):
            try: r = json.loads(ln)
            except Exception: continue
            tid = r.get("trade_id")
            key = (r.get("symbol"), tid)
            if tid is not None and key in seen[d]: continue
            if tid is not None: seen[d].add(key)
            nt = abs(float(r.get("fill_notional") or 0.0))
            notion += nt; n += 1
            c = r.get("commission")
            if c is not None: comm += float(c)
            if r.get("venue_maker_flag"): mk += 1
    per_day[d] = dict(notional=notion, commission=comm, n=n, maker=mk)

tot_n = sum(v["notional"] for v in per_day.values()); tot_c = sum(v["commission"] for v in per_day.values())
tot_f = sum(v["n"] for v in per_day.values()); tot_m = sum(v["maker"] for v in per_day.values())
print(f"\n[LIVE FILLS] n_fills(dedup by trade_id) {tot_f}  maker {tot_m} ({100*tot_m/max(tot_f,1):.1f}%)")
print(f"  traded notional total {tot_n:,.0f} USDT   commission total {tot_c:,.2f} USDT  "
      f"=> {1e4*tot_c/tot_n:+.3f} bps of traded notional")

# NAV / flows
nav = []
for d in days:
    f = f"{PL}/{d}/daily_nav.jsonl"
    if not os.path.exists(f): continue
    for ln in open(f):
        try: r = json.loads(ln)
        except Exception: continue
        nav.append(r)
nav = {r["day"]: r for r in nav}
dl = sorted(nav)
print(f"\n[NAV] {dl[0]}..{dl[-1]} n={len(dl)}")
rows = []
for d in dl:
    r = nav[d]
    pv = float(r.get("prev_nav") or 0); nv = float(r.get("nav") or 0)
    fl = float(r.get("external_flow_usdt") or 0)
    tg = float(r.get("target_gross") or 0)
    if pv > 0:
        ret = (nv - fl - pv) / pv
        rows.append((d, pv, nv, fl, ret, tg))
rr = np.array([x[4] for x in rows])
gr = np.array([x[5] for x in rows]); pvv = np.array([x[1] for x in rows])
lev = gr / np.where(pvv > 0, pvv, np.nan)
print(f"  flow-adjusted daily return: n={len(rr)} mean {100*rr.mean():+.4f}%/d sd {100*rr.std(ddof=1):.4f}%/d "
      f"Sharpe_ann {rr.mean()/rr.std(ddof=1)*np.sqrt(365):+.3f}  cum {100*(np.prod(1+rr)-1):+.3f}%")
print(f"  worst day {100*rr.min():+.4f}% on {rows[int(np.argmin(rr))][0]}   2nd {100*np.sort(rr)[1]:+.4f}%  3rd {100*np.sort(rr)[2]:+.4f}%")
print(f"  mean realized leverage (target_gross/prev_nav) {np.nanmean(lev):.3f}")

# per-day traded notional as fraction of gross -> realized turnover in book units
print(f"\n[REALIZED TURNOVER & COST, per day]")
print(f"  {'day':<10s}{'notional':>12s}{'gross':>10s}{'turn/gross':>11s}{'comm$':>9s}{'comm_bpsNAV':>12s}{'ret%':>8s}")
tt=[]; cc=[]
for d, pv, nv, fl, ret, tg in rows:
    dd = d.replace("-", "")
    v = per_day.get(dd)
    if not v or tg <= 0: continue
    t = v["notional"] / tg
    tt.append(t); cc.append(1e4 * v["commission"] / pv)
    print(f"  {d:<10s}{v['notional']:>12,.0f}{tg:>10,.0f}{t:>11.4f}{v['commission']:>9.2f}{1e4*v['commission']/pv:>12.3f}{100*ret:>8.3f}")
tt = np.array(tt); cc = np.array(cc)
print(f"  MEAN turnover/gross/day {tt.mean():.4f} (= {tt.mean()/6:.4f} per anchor, x2 sides)  "
      f"commission {cc.mean():.3f} bps of NAV/day")

# ---- the exchange rate ----
COST_PER_TURN = 3.870          # bps of gross per 1.0 |dw| (producer COST_B, calibrated part 5)
TURN = 0.0310                  # observed |dw| per anchor, unit gross (part 5)
LEV = 2.0
print(f"\n[EXCHANGE RATE — turnover cost vs tail]")
c_anchor = COST_PER_TURN * TURN
print(f"  modelled cost of the ENTIRE current turnover: {c_anchor:.4f} bps of gross/anchor")
print(f"    = {c_anchor*6:.3f} bps gross/day = {c_anchor*6*LEV:.3f} bps NAV/day = {c_anchor*6*LEV*365/100:.3f} %NAV/yr(365, simple)")
print(f"  realized commission bill: {cc.mean():.3f} bps NAV/day = {cc.mean()*365/100:.3f} %NAV/yr")
wd = 100*rr.min()
print(f"  the single worst day {wd:.3f}% NAV = {abs(wd)*100:.0f} bps NAV")
print(f"    = {abs(wd)*100/(c_anchor*6*LEV):.0f} days of the entire modelled turnover bill")
print(f"    = {abs(wd)*100/cc.mean():.0f} days of the entire realized commission bill")
for N in (17, 41, 90, 180, 365):
    dT = abs(wd)*100/(COST_PER_TURN*6*LEV*N)
    print(f"  break-even: removing ONE such day every {N:>3d} days pays for extra |dw| of "
          f"{dT:.4f}/anchor = {dT/TURN:5.1f}x the book's CURRENT total turnover")
