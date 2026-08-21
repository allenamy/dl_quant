#!/usr/bin/env python3
"""per_name_stop 30-day counterfactual backfill (PREREG_per_name_stop_standby_2026-08-12 §4 honesty clause).

For every name the live clause stopped, compare what actually happened (exit at the flatten fills) with the
counterfactual of HOLDING the position through the next 30 days (public daily klines, read-only, no keys):
  - realised exit P&L is already in the book; here we report the path AFTER the stop:
      cf_pnl_bps  = position_sign * (close_t / exit_px - 1) * 1e4   (bps of the position's notional)
      cf_nav_bps  = cf_pnl_bps * notional / NAV_at_stop              (bps of NAV)
    at horizons 1/3/7/14/30 days, plus max favourable / adverse excursion within 30 days.
  - a negative cf (price kept moving against the old position) means the stop SAVED money; positive = cost.
Partial windows are reported with `days_elapsed`; the formal reading is at 30 days (BOME 2026-09-19, ENA 2026-09-20).
Inputs (read-only): ~/dl_quant_live/state/live/pilot_log/*/{orders.jsonl,position_readback.jsonl,daily_nav.jsonl}
Output: results/per_name_stop_backfill_<date>.json + one line per name on stdout.
"""
import json, glob, os, sys, time, urllib.request, urllib.parse
LIVE = os.path.expanduser("~/dl_quant_live/state/live/pilot_log")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
os.makedirs(OUT, exist_ok=True)

def rows(pattern):
    out = []
    for f in sorted(glob.glob(os.path.join(LIVE, "*", pattern))):
        for l in open(f):
            l = l.strip()
            if l:
                try: out.append(json.loads(l))
                except Exception: pass
    return out

def klines(sym, start_ms, end_ms):
    q = urllib.parse.urlencode({"symbol": sym, "interval": "1d", "startTime": int(start_ms), "endTime": int(end_ms), "limit": 60})
    with urllib.request.urlopen("https://fapi.binance.com/fapi/v1/klines?" + q, timeout=20) as r:
        return json.loads(r.read().decode())

def main():
    ords = rows("orders.jsonl"); navs = rows("daily_nav.jsonl"); rb = rows("position_readback.jsonl")
    # stop exits: flatten_only channel rows are ordinary maker/taker rows with reduce_only intent and target_w == 0 on a
    # name under per_name_stop; we identify them by note/terminal fields mentioning per_name_stop, else by the cooldown list.
    cool = {}
    try: cool = json.load(open(os.path.expanduser("~/dl_quant_live/state/live/per_name_stop.json"))).get("cooldown") or {}
    except Exception: pass
    stopped = sorted(cool.keys())
    if not stopped: print("no stopped names"); return
    res = {}
    now_ms = int(time.time() * 1000)
    for sym in stopped:
        # the last anchor where the name had a position BEFORE the cooldown stamp: readback rows carry notional & side
        cd_ts = float(cool[sym]) - 7 * 86400          # cooldown stamp = flat-detected time + 7d (clause: cooloff_days=7)
        def _t(r):
            t = float(r.get("read_ts") or r.get("anchor_ts") or 0); return t / 1000 if t > 1e11 else t
        # last readback BEFORE the cooldown start where the name still carried a real position (≥ 5 USDT; dust stays after the exit)
        pos_rows = [r for r in rb if r.get("symbol") == sym and _t(r) <= cd_ts and abs(float(r.get("venue_position_notional") or 0.0)) >= 5.0]
        if not pos_rows:
            res[sym] = {"error": "no readback rows with a real position before stop"}; print(sym, "no readback rows"); continue
        last = max(pos_rows, key=_t)
        notional = float(last.get("venue_position_notional") or 0.0)
        sign = 1.0 if notional > 0 else -1.0
        # exit fills: orders on this symbol after that readback (up to the cooldown start) that reduce the position
        def _ot(o):
            t = float(o.get("submit_ts") or 0); return t / 1000 if t > 1e11 else t
        ex = [o for o in ords if o.get("symbol") == sym and _t(last) - 60 <= _ot(o) <= cd_ts + 3600 and float(o.get("filled_notional") or 0) != 0]
        ex = [o for o in ex if (sign > 0 and o.get("side") == "sell") or (sign < 0 and o.get("side") == "buy")]
        if not ex:
            res[sym] = {"error": "no exit fills found", "notional": notional}; print(sym, "no exit fills"); continue
        fn = sum(abs(float(o.get("filled_notional") or 0)) for o in ex)
        px = sum(float(o.get("avg_fill_px") or 0) * abs(float(o.get("filled_notional") or 0)) for o in ex) / fn
        t_exit = min(_ot(o) for o in ex)
        nav_rows = [r for r in navs if float(r.get("nav_ts") or 0) <= t_exit and r.get("nav")]
        nav0 = float(nav_rows[-1]["nav"]) if nav_rows else float("nan")
        ks = klines(sym, t_exit * 1000, min(now_ms, (t_exit + 31 * 86400) * 1000))
        closes = [float(k[4]) for k in ks]; highs = [float(k[2]) for k in ks]; lows = [float(k[3]) for k in ks]
        days = len(closes); cf = {}
        for h in (1, 3, 7, 14, 30):
            if days >= h:
                cf[f"d{h}_bps_pos"] = round(sign * (closes[h - 1] / px - 1) * 1e4, 1)
                cf[f"d{h}_bps_nav"] = round(sign * (closes[h - 1] / px - 1) * 1e4 * abs(notional) / nav0, 2) if nav0 == nav0 else None
        mfe = max([sign * ((highs[i] if sign > 0 else lows[i]) / px - 1) * 1e4 for i in range(days)], default=None)
        mae = min([sign * ((lows[i] if sign > 0 else highs[i]) / px - 1) * 1e4 for i in range(days)], default=None)
        res[sym] = {"side": "long" if sign > 0 else "short", "notional_at_stop": round(notional, 1), "exit_px": px, "exit_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t_exit)),
                    "nav_at_stop": nav0, "days_elapsed": days, "counterfactual_hold": cf, "mfe_bps_pos": None if mfe is None else round(mfe, 1), "mae_bps_pos": None if mae is None else round(mae, 1),
                    "reading": "cf<0 ⇒ the stop SAVED money (price kept going against the old position); cf>0 ⇒ the stop COST money (missed rebound)"}
        print(sym, res[sym]["side"], f"notional {notional:+.0f} exit {px} days {days} cf {cf} mfe {res[sym]['mfe_bps_pos']} mae {res[sym]['mae_bps_pos']}")
    stamp = time.strftime("%Y-%m-%d", time.gmtime())
    json.dump({"generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "names": res}, open(os.path.join(OUT, f"per_name_stop_backfill_{stamp}.json"), "w"), indent=1)

if __name__ == "__main__":
    main()
