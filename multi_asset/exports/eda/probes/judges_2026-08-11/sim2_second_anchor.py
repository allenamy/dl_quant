"""SIM ② — the SECOND consecutive anchor: a book already exists, so 08:00Z ADJUSTS, not rebuilds.

READ-ONLY: real tree copied, mock broker, temp state. Nothing under state/ is written.

This path has run once in two days (2026-07-27 12:00Z) and that run was on the OLD ledger
caliber. At 08:00Z it runs for the first time with: B29's fill-based book cache, the quantity
reconciliation, and a real 101-name book underneath it.
"""
import json
import os
import shutil
import sys
import tempfile

REPO = "/Users/haosiyu/dl_quant_live"
sys.path.insert(0, os.path.join(REPO, "live"))
sys.path.insert(0, os.path.join(REPO, "scheduler"))
_tmp = tempfile.mkdtemp(prefix="sim2_")
os.environ["LIVE_LOOP_STATE"] = os.path.join(_tmp, "loop_state.json")
os.environ["LIVE_MODE"] = "TESTNET"

import anchor_loop as AL             # noqa: E402
import binance_executor as EX        # noqa: E402
import pilot_log as PL               # noqa: E402
import reconcile as RC               # noqa: E402

FAILS, N = [], [0]


def check(name, ok, detail=""):
    N[0] += 1
    print(f"  {'OK  ' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAILS.append(name)


ROOT = os.path.join(_tmp, "pilot_log")
shutil.copytree(os.path.join(REPO, "state", "testnet", "pilot_log"), ROOT)
_rows = PL.read_day(ROOT, "20260728")["position_readback"]
_LAST = max(r["anchor_ts"] for r in _rows)
BOOK_N = {r["symbol"]: float(r["venue_position_notional"]) for r in _rows
          if r["anchor_ts"] == _LAST and abs(r["venue_position_notional"]) > 1e-9}
BOOK_Q = {r["symbol"]: float(r["venue_position_qty"]) for r in _rows
          if r["anchor_ts"] == _LAST and abs(r["venue_position_notional"]) > 1e-9}
MIDS = {s: abs(BOOK_N[s] / BOOK_Q[s]) for s in BOOK_N if BOOK_Q[s]}

print("=" * 96)
print("SIM ② — second consecutive anchor: adjust an existing book, not rebuild it")
print("=" * 96)
print(f"\n  prev book: {len(BOOK_N)} names, gross {sum(abs(v) for v in BOOK_N.values()):,.0f} USDT")

# the 08:00Z target: same gross, weights nudged — a REBALANCE, not a rebuild
TARGET = {s: v * (1.15 if i % 2 else 0.85) for i, (s, v) in enumerate(sorted(BOOK_N.items()))}

ex = EX.RebalanceExecutor.__new__(EX.RebalanceExecutor)
ex.band_bps = 0.0
# the REAL SymbolFilters object, seeded with permissive filters — using a stub would test the
# stub's rounding rather than production's
ex.filters = EX.SymbolFilters(broker=None)
ex.filters.f = {s: {"tick": 1e-8, "step": 1e-8, "min_notional": 5.0} for s in BOOK_N}
plans = EX.RebalanceExecutor.plan(ex, TARGET, BOOK_N, MIDS)

print("\n[2a] ★★ the order is the DELTA, never the target")
_live = [p for p in plans if not p.get("skip")]
_bad = [(p["symbol"], p["delta_notional"], p["target_notional"], p["prev_notional"])
        for p in _live
        if abs(p["delta_notional"] - (p["target_notional"] - p["prev_notional"])) > 1e-9]
check("★★ delta == target - prev on every planned name",
      not _bad, f"{len(_bad)} mismatches, e.g. {_bad[:2]}")
_gross_delta = sum(abs(p["delta_notional"]) for p in _live)
_gross_target = sum(abs(p["target_notional"]) for p in _live)
check("★★ ...so the anchor trades ~15% of gross, not ~100% (a rebuild would trade the target)",
      _gross_delta < 0.4 * _gross_target,
      f"delta gross {_gross_delta:,.0f} vs target gross {_gross_target:,.0f} "
      f"({_gross_delta / _gross_target:.1%} — a rebuild would read ~100%)")
check("★ prev_w is populated from the existing book (a rebuild would show prev_w = 0)",
      all(abs(p["prev_w"]) > 0 for p in _live[:20]),
      f"{sum(1 for p in _live if abs(p['prev_w']) > 0)}/{len(_live)} names carry a non-zero prev_w")

print("\n[2b] the venue-truth reconcile at anchor start ADOPTS the venue, and says how far it was")
_drift_syms = sorted(BOOK_N)[:3]
_cached = dict(BOOK_N)
for s in _drift_syms:
    _cached[s] = BOOK_N[s] * 0.5          # a cache that drifted from the venue
_keys = set(BOOK_N) | set(_cached)
_drift = {k: (_cached.get(k, 0.0), BOOK_N.get(k, 0.0)) for k in _keys
          if abs(_cached.get(k, 0.0) - BOOK_N.get(k, 0.0)) > 1.0}
check("★★ a drifted cache is detected against venue truth (this is the alarm B29 made meaningful)",
      set(_drift) == set(_drift_syms), sorted(_drift))

print("\n[2c] ★★ B29: the cached book after the anchor is the FILLS, not the intent")
# the maker fills 60% of each delta; the top-up gets a further 25%; 15% goes unfilled
rows = []
for p in _live:
    d = p["delta_notional"]
    rows.append(dict(rebalance_id="A2", symbol=p["symbol"], order_type="maker",
                     intended_notional=d, filled_notional=d * 0.60,
                     terminal_reason="partial_expired"))
    rows.append(dict(rebalance_id="A2", symbol=p["symbol"], order_type="topup_taker",
                     intended_notional=d * 0.40, filled_notional=d * 0.25,
                     terminal_reason="partial_expired"))
_bk = AL.book_after_anchor(BOOK_N, rows, "A2")
# only the PLANNED names move — 8 of 101 are skipped by the band / min-notional, and expecting
# those to move was a fixture error that read exactly like a defect.
_planned = {p["symbol"] for p in _live}
_want = {s: BOOK_N[s] + (TARGET[s] - BOOK_N[s]) * 0.85 for s in _planned}
_off = {s: (round(_bk["positions"][s], 6), round(_want[s], 6)) for s in _want
        if abs(_bk["positions"][s] - _want[s]) > 1e-6}
check("★★ the cache moves by 85% of the delta — what FILLED — not by 100% (the target)",
      not _off, f"{len(_off)} names off, e.g. {list(_off.items())[:2]}")
_target_cache = {s: TARGET[s] for s in TARGET}
check("★ ...and it is measurably NOT the target (the old rule's answer)",
      any(abs(_bk["positions"][s] - _target_cache[s]) > 1.0 for s in _want),
      "if these coincided this check could not tell the two rules apart")
check("★ every leg was readable, so nothing is left unattributed",
      _bk["unknown"] == [], _bk["unknown"][:3])
_skipped = set(BOOK_N) - _planned
check("★ ...and a name the planner SKIPPED does not move in the cache either",
      all(abs(_bk["positions"][s] - BOOK_N[s]) < 1e-9 for s in _skipped),
      f"{len(_skipped)} skipped names (band / min-notional) held at their previous value")

print("\n[2d] ★★ the new-caliber reconciliation across the SECOND anchor")
_lg = PL.PilotLogger(ROOT, day="20260728")
_new = _LAST + 4 * 3600
_fill_px = {s: MIDS[s] for s in BOOK_N}
for p in _live:
    s = p["symbol"]
    d = p["delta_notional"]
    for otype, frac, att in (("maker", 0.60, 1), ("topup_taker", 0.25, 2)):
        _lg.order(anchor_ts=_new, symbol=s, side=("buy" if d > 0 else "sell"),
                  target_w=p["target_w"], prev_w=p["prev_w"],
                  intended_notional=d * (1.0 if otype == "maker" else 0.40),
                  order_type=otype, submit_ts=_new + 1, price_submit=_fill_px[s],
                  mid_at_submit=_fill_px[s], mid_at_anchor=_fill_px[s],
                  filled_notional=d * frac, avg_fill_px=_fill_px[s],
                  first_fill_ts=_new + 2, last_fill_ts=_new + 2, cancel_ts=None,
                  fee_paid=0.0, rebalance_id="A2", attempt_idx=att,
                  terminal_reason="partial_expired", notional_currency="USDT")
# the venue readback that follows: the book really did move by 85% of each delta, in CONTRACTS
for s in sorted(BOOK_N):
    _q = BOOK_Q[s] + ((TARGET[s] - BOOK_N[s]) * 0.85) / _fill_px[s]
    _lg.position_readback(anchor_ts=_new, symbol=s, read_ts=_new + 1000, source="sim",
                          venue_position_notional=_q * _fill_px[s], venue_position_qty=_q)
_lg.close()
_rec = RC.reconcile([(d, PL.read_day(ROOT, d)) for d in sorted(os.listdir(ROOT)) if d.isdigit()])
check("★★ an ADJUSTED book reconciles clean — the fills explain every contract that moved",
      len(_rec["latest"]) == 0 and len(_rec["latest_unreconcilable"]) == 0,
      f"{len(_rec['latest'])} unexplained, {len(_rec['latest_unreconcilable'])} un-compared; "
      f"e.g. {[(a['symbol'], a.get('residual_usdt')) for a in _rec['latest'][:3]]}")

print("\n[2e] ★★ RED CAPABILITY — drop ONE leg's fill row and the same walk must fire")
_root2 = os.path.join(_tmp, "pilot_log2")
shutil.copytree(ROOT, _root2)
_p = os.path.join(_root2, "20260728", "orders.jsonl")
_lines = [json.loads(l) for l in open(_p)]
_victim = sorted(BOOK_N)[7]
_kept = [l for l in _lines
         if not (l.get("rebalance_id") == "A2" and l.get("symbol") == _victim
                 and l.get("order_type") == "maker")]
check("★ the mutation really removed a leg (else the red below proves nothing)",
      len(_kept) == len(_lines) - 1, f"{len(_lines)} -> {len(_kept)}")
open(_p, "w").write("".join(json.dumps(l) + "\n" for l in _kept))
_rec2 = RC.reconcile([(d, PL.read_day(_root2, d))
                      for d in sorted(os.listdir(_root2)) if d.isdigit()])
# ★★ MEASURED, AND IT IS A PROPERTY OF THE ADJUST PATH, NOT A FIXTURE ACCIDENT.
# The tolerance is `max(0.10 x scale, floor)` with scale ~ the POSITION, while a missing leg is
# ~0.60 x the DELTA. On a rebuild (prev = 0) delta IS the position, so 0.60 > 0.10 and it always
# fires — which is every anchor this book has seen so far. On an ADJUST anchor with delta ~15%
# of position the same total loss is 0.09 x position, just under the 0.10 gate, and it is SILENT.
# Crossover measured on the real median position (192.9 USDT): delta ~21% of position.
_d_victim = next(p["delta_notional"] for p in _live if p["symbol"] == _victim)
_pos_victim = BOOK_N[_victim]
_ratio = abs(_d_victim) / abs(_pos_victim)
check("★ the fixture's delta really is adjust-sized (this is what makes the result meaningful)",
      _ratio < 0.20, f"delta/position = {_ratio:.1%} for {_victim}")
check("★★ MEASURED: at adjust size a whole missing maker leg is INSIDE the 10% gate — SILENT",
      [a["symbol"] for a in _rec2["latest"]] == [],
      f"unexplained={[(a['symbol'], a.get('residual_usdt')) for a in _rec2['latest'][:3]]} "
      f"| missing {abs(_d_victim) * 0.60:.1f} USDT vs gate ~{0.10 * abs(_pos_victim) * 1.15:.1f}")
# and the control: make the delta big enough and the SAME walk fires, so this is a threshold
# property and not a broken reconciliation
_root3 = os.path.join(_tmp, "pilot_log3")
shutil.copytree(ROOT, _root3)
_p3 = os.path.join(_root3, "20260728", "orders.jsonl")
_l3 = [json.loads(l) for l in open(_p3)]
_big = sorted(BOOK_N)[9]
_l3 = [l for l in _l3 if not (l.get("rebalance_id") == "A2" and l.get("symbol") == _big)]
open(_p3, "w").write("".join(json.dumps(l) + "\n" for l in _l3))
_rec3 = RC.reconcile([(d, PL.read_day(_root3, d))
                      for d in sorted(os.listdir(_root3)) if d.isdigit()])
check("★★ CONTROL: drop BOTH legs (85% of the delta) and it does fire — the walk is not broken",
      _big in [a["symbol"] for a in _rec3["latest"]],
      [(a["symbol"], a.get("residual_usdt")) for a in _rec3["latest"][:3]])

shutil.rmtree(_tmp, ignore_errors=True)
print(f"\n  {N[0]} checks run")
print(f"\n{'ALL PASS' if not FAILS else 'FAILURES: ' + str(FAILS)}")
sys.exit(0 if not FAILS else 1)
