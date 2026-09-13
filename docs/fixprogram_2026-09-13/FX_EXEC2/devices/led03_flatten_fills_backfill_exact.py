#!/usr/bin/python3
"""LED-03 EXACT fee backfill for the eight older protective-flatten batches (1,210 legs, 270,076.47 USDT) — CREDENTIALED,
for the lead to run. Committed BEFORE any run; never run by FX-EXEC2 (no credentials loaded here).

Why a new device: before 09-10 (d73b1b0) the ladder sent no client id, so ops/backfill_fills.py builds zero legs for these
batches and refuses to write. This device attributes by (symbol, side, batch window) instead, and PROVES each leg closes:
  window  = [trip time from FLATTEN-<trip> − 5 s, the batch rows' write time (anchor_ts) + 5 s]
  trades  = GET /fapi/v1/userTrades (symbol, startTime, endTime) — signed GET, weight 5, paced by the broker's budget
  keep    = side equals the order row's side AND (symbol, id) not already in ANY fills row of the day
  close   = Σ quoteQty equals the order row's |filled_notional| within max(0.01 USDT, 1e-6 relative)  ⇒ attributable
  else    ⇒ leg SKIPPED and named (not_closing / no_trades / read_failed); never partially written
Rows written per trade, same columns as the E1 backfill rows (order_type protective_flatten, the batch rebalance_id, the
ORDER ROW's attempt_idx (not the venue_fills 1/2 convention, fact table NEW-02), commission + commission_asset as the venue
reports them, mid_at_fill_plus_60s None with the pending note, backfilled_utc) through pilot_log.PilotLogger.fill
(under the LED-01 guard when the executor tree has it).
Modes: (default) REPORT — reads the venue, writes nothing; --rehearse — writes into a temp root (this day COPIED, other
days SYMLINKED), watchdog.evaluate before/after, applies twice (second writes 0), live day files unchanged; --apply —
backup of the day's fills.jsonl beside it (…pre_led03_<utc>), append, re-read, idempotent.
Usage (lead): LIVE_MODE=LIVE /usr/bin/python3 led03_flatten_fills_backfill_exact.py --repo ~/dl_quant_live \
      --root ~/dl_quant_live/state/live --day 20260906 --rid FLATTEN-20260906T084608Z --receipt OUT [--rehearse|--apply]"""
import argparse, calendar, collections, hashlib, json, os, shutil, sys, tempfile, time
ap = argparse.ArgumentParser(allow_abbrev=False)
for k in ("--repo", "--root", "--day", "--rid", "--receipt"): ap.add_argument(k, required=True)
ap.add_argument("--rehearse", action="store_true"); ap.add_argument("--apply", action="store_true")
a = ap.parse_args()
if a.rehearse and a.apply: raise SystemExit("choose one of --rehearse / --apply")
for d in ("live", "ops", "scheduler", "signal"): sys.path.insert(0, os.path.join(a.repo, d))
os.chdir(a.repo)
import envfile; envfile.load(os.path.join(a.repo, ".env"))
os.environ["LIVE_MODE"] = "LIVE"; os.environ.setdefault("BINANCE_LIVE_CONFIRM", "I_UNDERSTAND")
import binance_broker as BB, pilot_log as PL, watchdog as WD
TOL_ABS, TOL_REL, SLACK = 0.01, 1e-6, 5.0
def day_rows(root, table):
    p = os.path.join(root, "pilot_log", a.day, f"{table}.jsonl")
    return [json.loads(l) for l in open(p) if l.strip()] if os.path.exists(p) else []
orders = [o for o in day_rows(a.root, "orders") if o.get("rebalance_id") == a.rid]
if not orders: raise SystemExit(f"no order rows for {a.rid} in {a.day}")
trip = calendar.timegm(time.strptime(a.rid.split("-", 1)[1], "%Y%m%dT%H%M%SZ"))
t0_ms, t1_ms = int((trip - SLACK) * 1000), int((max(float(o["anchor_ts"]) for o in orders) + SLACK) * 1000)
broker = BB.BinanceBroker(mode="LIVE"); arm = broker.arm()
def build(root):
    have = {(f.get("symbol"), f.get("trade_id")) for f in day_rows(root, "fills") if f.get("trade_id") is not None}
    legs, rows = [], []
    for o in orders:
        fa = o.get("filled_notional")
        if fa is None or abs(float(fa)) <= 0: continue
        sym, side = o["symbol"], str(o.get("side") or "").upper()
        try:
            tr = broker._request("GET", "/fapi/v1/userTrades", {"symbol": sym, "startTime": t0_ms, "endTime": t1_ms, "limit": 1000}, signed=True) or []
        except Exception as e:
            legs.append({"symbol": sym, "state": "read_failed", "error": f"{type(e).__name__}: {str(e)[:120]}"}); continue
        keep = [t for t in tr if str(t.get("side", "")).upper() == side and (sym, int(t["id"])) not in have]
        if not keep:
            legs.append({"symbol": sym, "state": "no_trades" if not tr else "already_present_or_other_side", "n_trades_window": len(tr)}); continue
        q = sum(float(t.get("quoteQty") or 0.0) for t in keep)
        if abs(q - abs(float(fa))) > max(TOL_ABS, TOL_REL * abs(float(fa))):
            legs.append({"symbol": sym, "state": "not_closing", "sum_quote": q, "order_notional": abs(float(fa)), "n_trades": len(keep)}); continue
        comm = collections.defaultdict(float)
        for t in keep:
            comm[t.get("commissionAsset")] += float(t.get("commission") or 0.0)
            rows.append({"anchor_ts": o["anchor_ts"], "symbol": sym, "side": side.lower(), "order_type": "protective_flatten",
                         "attempt_idx": int(o.get("attempt_idx") or 1), "fill_ts": int(t["time"]) / 1000.0,
                         "fill_px": float(t["price"]), "fill_notional": float(t["quoteQty"]), "mid_at_fill_plus_60s": None,
                         "rebalance_id": a.rid, "trade_id": int(t["id"]), "commission": float(t.get("commission") or 0.0),
                         "commission_asset": t.get("commissionAsset"), "venue_maker_flag": bool(t.get("maker")),
                         "mid_at_fill_plus_60s_note": "not yet observable when this row was written (the +60s mark had not passed or its 1m candle had not closed); pending backfill, NOT zero",
                         "backfilled_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "backfill_source": "LED-03 exact (symbol, side, batch window)"})
        legs.append({"symbol": sym, "state": "attributable", "n_trades": len(keep), "commission_by_asset": dict(comm)})
    return legs, rows
def write(root, rows):
    lg = PL.PilotLogger(os.path.join(root, "pilot_log"), day=a.day); n = q = 0
    try:
        for r in rows:
            ok = lg.fill(**r)
            if ok is False: q += 1
            else: n += 1
    finally:
        lg.close()
    return {"written": n, "quarantined": q}
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest() if os.path.exists(p) else None
res = {"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "rid": a.rid, "day": a.day, "window_ms": [t0_ms, t1_ms],
       "arm_ok": bool(arm.get("armed")), "mode": "rehearse" if a.rehearse else ("apply" if a.apply else "report"),
       "live_fills_sha_before": sha(os.path.join(a.root, "pilot_log", a.day, "fills.jsonl"))}
if a.rehearse:
    tmp = tempfile.mkdtemp(prefix="led03_rehearsal_"); pl = os.path.join(tmp, "pilot_log"); os.makedirs(pl)
    src = os.path.join(os.path.abspath(a.root), "pilot_log")
    for d in os.listdir(src):
        (shutil.copytree if d == a.day else os.symlink)(os.path.join(src, d), os.path.join(pl, d))
    ev0 = WD.evaluate(pl, venue_events=[], ops_stats=[])
    legs, rows = build(tmp); res["legs"] = legs; res["apply_1"] = write(tmp, rows)
    legs2, rows2 = build(tmp); res["apply_2_rows_found"] = len(rows2); res["apply_2"] = write(tmp, rows2)
    ev1 = WD.evaluate(pl, venue_events=[], ops_stats=[])
    res["watchdog_tripped_before_after"] = [ev0.get("tripped"), ev1.get("tripped")]
    res["watchdog_blind_before_after"] = [ev0.get("conditions_blind"), ev1.get("conditions_blind")]
elif a.apply:
    p = os.path.join(a.root, "pilot_log", a.day, "fills.jsonl")
    bak = p + ".pre_led03_" + time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    if os.path.exists(p): shutil.copy2(p, bak)
    legs, rows = build(a.root); res["legs"] = legs; res["apply"] = write(a.root, rows); res["backup"] = bak
    res["prefix_preserved"] = (open(p, "rb").read()[:os.path.getsize(bak)] == open(bak, "rb").read()) if os.path.exists(bak) else None
else:
    legs, rows = build(a.root); res["legs"] = legs; res["rows_recoverable"] = len(rows)
res["legs_by_state"] = dict(collections.Counter(l["state"] for l in res.get("legs", [])))
res["live_fills_sha_after"] = sha(os.path.join(a.root, "pilot_log", a.day, "fills.jsonl"))
res["live_untouched"] = (res["live_fills_sha_after"] == res["live_fills_sha_before"]) if not a.apply else None
json.dump(res, open(a.receipt, "w"), indent=1, default=str)
print("LED03_EXACT", res["mode"], res["rid"], res["legs_by_state"], {k: res.get(k) for k in ("rows_recoverable", "apply_1", "apply_2", "apply", "watchdog_tripped_before_after", "live_untouched", "prefix_preserved")})
