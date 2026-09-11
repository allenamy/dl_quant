#!/usr/bin/env python3
"""r11 STEP 1 — export deduped live fills (+ position context) as the input to the multi-lag markout device.

READ-ONLY on /Users/haosiyu/dl_quant_live.

DEDUPE (copied from trackB_realized_cost_2026-09-11.py, sha16 9eb531f4269ed2ae):
  key = (symbol, trade_id); when the same key appears twice keep the row that carries
  mid_at_fill_plus_60s (the backfilled row supersedes).

ENTRY / ADD / SHED classification (this script's own definition, stated because nothing upstream defines it):
  prev = venue_position_notional for (symbol) at the LAST position_readback anchor STRICTLY BEFORE this
  fill's anchor_ts.  signed fill f = +notional for buy, -notional for sell.
    |prev| <= EPS_USDT                -> ENTRY   (age 0: the book had no seat in this name)
    sign(f) == sign(prev)             -> ADD     (increasing an existing seat)
    sign(f) != sign(prev)             -> SHED    (reducing / flipping an existing seat)
  EPS_USDT = 1.0 (a seat below one dollar is flat; venue dust).

ENV WHITELIST: {} (empty) — asserted (E-0826-D).
"""
import json, os, hashlib, datetime as dt

_FORBID = ("CAL","JUDGE","PANEL","EXPORT_PANEL","EMA_STATE_JSON","W10_","POD_","DLW_","KING_","SEAT_","UMASK")
_hits = sorted(k for k in os.environ if any(k.startswith(p) for p in _FORBID))
assert not _hits, f"ENV WHITELIST VIOLATION: {_hits}"
ENV_WHITELIST = {}

LOG = "/Users/haosiyu/dl_quant_live/state/live/pilot_log"
OUT = "/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11/r11_costtruth/out"
EPS_USDT = 1.0

days = sorted(d for d in os.listdir(LOG) if d.isdigit())

# ---------- anchors (for BNB mid, used by the fee side) ----------
anch = {}
for d in days:
    p = f"{LOG}/{d}/anchors.jsonl"
    if not os.path.exists(p): continue
    for ln in open(p):
        r = json.loads(ln); ts = r.get("anchor_ts")
        if ts is None: continue
        mid = r.get("mid_at_anchor_vector")
        if isinstance(mid, str): mid = json.loads(mid)
        anch[ts] = dict(day=d, mid=mid or {}, realized_gross=r.get("realized_gross"),
                        target_gross=r.get("target_gross"), regime=r.get("regime_at_anchor"))
ats = sorted(anch)

# ---------- position readback: seat at each anchor ----------
pos = {}   # anchor_ts -> {symbol: venue_position_notional}
for d in days:
    p = f"{LOG}/{d}/position_readback.jsonl"
    if not os.path.exists(p): continue
    for ln in open(p):
        r = json.loads(ln)
        pos.setdefault(r["anchor_ts"], {})[r["symbol"]] = float(r.get("venue_position_notional") or 0.0)
pts = sorted(pos)

import bisect
def prev_seat(anchor_ts, symbol):
    """venue position in `symbol` at the last readback anchor STRICTLY before anchor_ts."""
    i = bisect.bisect_left(pts, anchor_ts) - 1
    while i >= 0:
        if symbol in pos[pts[i]]:
            return pos[pts[i]][symbol], pts[i]
        i -= 1
    return None, None

# ---------- fills: dedupe ----------
raw_n = 0; F = {}; dupe_same = 0; dupe_diff = 0
for d in days:
    p = f"{LOG}/{d}/fills.jsonl"
    if not os.path.exists(p): continue
    for ln in open(p):
        r = json.loads(ln); raw_n += 1
        k = (r["symbol"], r["trade_id"])
        cur = F.get(k)
        if cur is None:
            F[k] = r; continue
        same = (cur.get("fill_notional") == r.get("fill_notional") and cur.get("commission") == r.get("commission")
                and cur.get("fill_px") == r.get("fill_px"))
        dupe_same += same; dupe_diff += (not same)
        if r.get("mid_at_fill_plus_60s") is not None and cur.get("mid_at_fill_plus_60s") is None:
            F[k] = r
fills = list(F.values())

rows = []
cls_count = {"ENTRY":0,"ADD":0,"SHED":0,"UNKNOWN":0}
for r in fills:
    ats_ = r.get("anchor_ts"); fts = r.get("fill_ts")
    if ats_ is None or fts is None: continue
    nz = abs(float(r.get("fill_notional") or 0.0))
    sgn = 1.0 if r.get("side") == "buy" else -1.0
    prev, prev_anchor = prev_seat(ats_, r["symbol"])
    if prev is None:
        cls = "UNKNOWN"
    elif abs(prev) <= EPS_USDT:
        cls = "ENTRY"
    elif (sgn > 0) == (prev > 0):
        cls = "ADD"
    else:
        cls = "SHED"
    cls_count[cls] += 1
    rows.append(dict(
        trade_id=r["trade_id"], symbol=r["symbol"], side=r["side"], sign=sgn,
        order_type=r.get("order_type"), attempt_idx=r.get("attempt_idx"),
        fill_ts=float(fts), fill_px=float(r.get("fill_px") or 0.0), notional=nz,
        anchor_ts=float(ats_), day=anch.get(ats_, {}).get("day"),
        venue_maker_flag=r.get("venue_maker_flag"),
        commission=float(r.get("commission") or 0.0), commission_asset=r.get("commission_asset") or "USDT",
        recorded_mid60=r.get("mid_at_fill_plus_60s"),
        recorded_mark_lag_s=r.get("mark_lag_s"), recorded_mark_source=r.get("mark_source"),
        recorded_mark_ts=r.get("mark_ts_actual"),
        seat_prev=prev, seat_class=cls, rebuilt_from_venue=r.get("rebuilt_from_venue"),
    ))

payload = dict(
    generated_utc=dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    env_whitelist=ENV_WHITELIST,
    source_log=LOG, days=[days[0], days[-1]], n_days=len(days),
    raw_rows=raw_n, deduped=len(fills), dupes_identical=dupe_same, dupes_differing=dupe_diff,
    seat_class_counts=cls_count, eps_usdt=EPS_USDT,
    rows=rows,
)
os.makedirs(OUT, exist_ok=True)
p = f"{OUT}/r11_fills_input.json"
with open(p, "w") as f:
    json.dump(payload, f)
sha = hashlib.sha256(open(p,"rb").read()).hexdigest()
print(f"raw {raw_n} -> deduped {len(fills)} (identical dupes {dupe_same}, differing {dupe_diff})")
print("seat_class:", cls_count)
print(f"wrote {p}  sha256={sha}  sha16={sha[:16]}  n_rows={len(rows)}")
# anchors BNB side-table for the fee analysis
with open(f"{OUT}/r11_anchor_bnb.json","w") as f:
    json.dump({str(t): dict(day=anch[t]["day"], bnb=anch[t]["mid"].get("BNBUSDT"),
                            realized_gross=anch[t]["realized_gross"], target_gross=anch[t]["target_gross"],
                            regime=anch[t].get("regime")) for t in ats}, f)
print("wrote r11_anchor_bnb.json  anchors=", len(ats))
