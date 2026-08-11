"""SIM ③ — the DERISK rungs (6..8 => 50%, 9..11 => 25%), a path that has never executed.

READ-ONLY: temp state file, mock broker, copied tree. Nothing under state/ is touched.

Asserted, per the brief: the cut is sized in CONTRACTS; chunking/min-notional compliance;
and the rows land in the ledger with a real submit_ts.
"""
import json
import os
import shutil
import sys
import tempfile

REPO = "/Users/haosiyu/dl_quant_live"
sys.path.insert(0, os.path.join(REPO, "live"))
sys.path.insert(0, os.path.join(REPO, "scheduler"))

_tmp = tempfile.mkdtemp(prefix="sim3_")
os.environ["LIVE_LOOP_STATE"] = os.path.join(_tmp, "loop_state.json")
os.environ["LIVE_MODE"] = "TESTNET"

import anchor_loop as AL             # noqa: E402
import pilot_log as PL               # noqa: E402
import reconcile as RC               # noqa: E402

FAILS, N = [], [0]


def check(name, ok, detail=""):
    N[0] += 1
    print(f"  {'OK  ' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAILS.append(name)


# the real book at 04:17:28Z, in BOTH calibers (contracts derived from the recorded qty column)
def real_book():
    rows = PL.read_day(os.path.join(REPO, "state", "testnet", "pilot_log"),
                       "20260728").get("position_readback", [])
    last = max(r["anchor_ts"] for r in rows)
    notional, contracts = {}, {}
    for r in rows:
        if r["anchor_ts"] != last or abs(r["venue_position_notional"]) < 1e-9:
            continue
        notional[r["symbol"]] = float(r["venue_position_notional"])
        contracts[r["symbol"]] = float(r["venue_position_qty"])
    return notional, contracts


class Broker:
    def __init__(self, contracts, notional):
        self.mode = "TESTNET"
        self.open_orders_halted = False
        self._c = dict(contracts)
        self._n = dict(notional)
        self.orders = []

    def positions(self):
        return dict(self._c)

    def positions_notional(self):
        return dict(self._n)

    def submit(self, order, reason=""):
        self.orders.append(dict(order, reason=reason))
        # the venue fills a reduce-only IOC immediately
        s, q = order["symbol"], order["quantity"]
        sign = -1.0 if order["side"] == "sell" else 1.0
        self._c[s] = self._c.get(s, 0.0) + sign * q
        return True


NOTIONAL, CONTRACTS = real_book()
print("=" * 96)
print("SIM ③ — DERISK ladder, offline, on the real 04:17:28Z book")
print("=" * 96)
print(f"\n  book: {len(CONTRACTS)} names, gross {sum(abs(v) for v in NOTIONAL.values()):,.0f} USDT")


def fresh_loop():
    b = Broker(CONTRACTS, NOTIONAL)
    loop = AL.AnchorLoop(b, executor=None, gross_usdt=25_000, log=None,
                         alarm=lambda sev, m: None)
    st = {"positions": dict(NOTIONAL), "stale_ref_positions": None,
          "stale_ref_contracts": None, "alarmed_stages": []}
    return b, loop, st


print("\n[3a] the cut is sized in CONTRACTS, and proportionally")
b, loop, st = fresh_loop()
st["stale_ref_positions"] = dict(NOTIONAL)
out = loop._scale_to(st, 0.50)
_sym = sorted(CONTRACTS)[0]
_want = {s: abs(CONTRACTS[s] * 0.5) for s in CONTRACTS}
_got = {o["symbol"]: o["quantity"] for o in b.orders}
_bad = {s: (round(_got.get(s, 0), 8), round(_want[s], 8)) for s in _want
        if abs(_got.get(s, 0.0) - _want[s]) > 1e-6}
check("★★ every cut equals |ref_contracts x (1-frac)|, i.e. CONTRACTS not notional",
      not _bad, f"{len(_bad)} mismatches, e.g. {list(_bad.items())[:2]}")
check("★ every order is reduce_only IOC (it must compose with a watchdog halt)",
      all(o["reduce_only"] and o["tif"] == "IOC" for o in b.orders),
      {(o["reduce_only"], o["tif"]) for o in b.orders})
_longs = [s for s in CONTRACTS if CONTRACTS[s] > 0]
_shorts = [s for s in CONTRACTS if CONTRACTS[s] < 0]
check("★★ a LONG is cut by SELLING and a SHORT by BUYING (sign, on real mixed data)",
      all(_got and next(o for o in b.orders if o["symbol"] == s)["side"] == "sell"
          for s in _longs[:5])
      and all(next(o for o in b.orders if o["symbol"] == s)["side"] == "buy"
              for s in _shorts[:5]),
      f"{len(_longs)} longs / {len(_shorts)} shorts in the real book")

print("\n[3b] idempotence — re-running the SAME rung must emit nothing")
n_before = len(b.orders)
loop._scale_to(st, 0.50)
check("★★ the second call at the same rung emits no orders (already at target)",
      len(b.orders) == n_before, f"{len(b.orders) - n_before} extra orders")

print("\n[3c] ★★ the rung REFERENCE must survive the process boundary")
# Each anchor is a NEW process: the ladder's reference is only meaningful if it is persisted.
b2, loop2, st2 = fresh_loop()
st2["stale_ref_positions"] = dict(NOTIONAL)
loop2._scale_to(st2, 0.50)                      # rung 6..8
AL._save(os.environ["LIVE_LOOP_STATE"], st2)
st_reloaded = AL._load(os.environ["LIVE_LOOP_STATE"], {})
check("★★ `stale_ref_contracts` is written into the state file the next process reads",
      st_reloaded.get("stale_ref_contracts") is not None,
      f"keys persisted: {sorted(st_reloaded)}")
# now the 25% rung, in a NEW loop that loads the persisted state
b3 = Broker(b2._c, NOTIONAL)                    # the venue book after the 50% cut
loop3 = AL.AnchorLoop(b3, executor=None, gross_usdt=25_000, log=None, alarm=lambda s, m: None)
st3 = dict(st_reloaded)
loop3._scale_to(st3, 0.25)
_after = b3._c
_want25 = {s: CONTRACTS[s] * 0.25 for s in CONTRACTS}
_bad25 = {s: (round(_after.get(s, 0), 6), round(_want25[s], 6)) for s in _want25
          if abs(_after.get(s, 0.0) - _want25[s]) > 1e-6}
check("★★ after the 9..11 rung the book is 25% of the PRE-STALE ref, not 25% of the 50% book",
      not _bad25,
      f"{len(_bad25)} names off; e.g. {list(_bad25.items())[:2]} "
      f"(12.5% would mean the reference was re-taken after the first cut)")

print("\n[3d] ★★ does a DERISK cut reach the ORDERS TABLE?")
root = os.path.join(_tmp, "pilot_log")
shutil.copytree(os.path.join(REPO, "state", "testnet", "pilot_log"), root)
_before_rows = len(PL.read_day(root, "20260728").get("orders", []))
b4, loop4, st4 = fresh_loop()
loop4.log = PL.PilotLogger(root, day="20260728")
st4["stale_ref_positions"] = dict(NOTIONAL)
loop4._scale_to(st4, 0.50)
loop4.log.close()
_after_rows = len(PL.read_day(root, "20260728").get("orders", []))
check("★★ a DERISK cut writes order rows (else §4-5b cannot explain the position change)",
      _after_rows > _before_rows,
      f"orders rows {_before_rows} -> {_after_rows}; venue orders submitted: {len(b4.orders)}")

print("\n[3e] ★★ ...and what §4-5b concludes about a book the ladder just cut")
# write the post-cut readback, as an anchor would, and reconcile
_lg = PL.PilotLogger(root, day="20260728")
_last = max(r["anchor_ts"] for r in PL.read_day(root, "20260728")["position_readback"])
_new = _last + 4 * 3600
for s in sorted(CONTRACTS):
    _lg.position_readback(anchor_ts=_new, symbol=s, read_ts=_new + 60, source="sim",
                          venue_position_notional=NOTIONAL[s] * 0.5,
                          venue_position_qty=b4._c.get(s, 0.0))
_lg.close()
_rec = RC.reconcile([(d, PL.read_day(root, d))
                     for d in sorted(os.listdir(root)) if d.isdigit()])
check("★★ the ladder's own de-risking is EXPLAINED, not reported as an unexplained position",
      len(_rec["latest"]) == 0,
      f"{len(_rec['latest'])} unexplained names, e.g. "
      f"{[(a['symbol'], a.get('residual_usdt')) for a in _rec['latest'][:3]]}")

print("\n[3f] chunking / minimum-notional compliance of the cut")
_ex_path = os.path.join(REPO, "live", "binance_executor.py")
_src = open(_ex_path).read()
_al = open(os.path.join(REPO, "scheduler", "anchor_loop.py")).read()
_scale_src = _al[_al.index("def _scale_to"):]
_scale_src = _scale_src[:_scale_src.index("\n    @")] if "\n    @" in _scale_src else _scale_src
check("★ the DERISK submit goes through a chunking / max-qty path",
      "chunk" in _scale_src.lower() or "max_qty" in _scale_src.lower(),
      "a raw quantity above MARKET_MAX_QTY is refused by the venue; the rebalance path chunks, "
      "this one calls broker.submit directly")
check("★ ...and respects the per-symbol minimum notional",
      "min_notional" in _scale_src.lower(),
      "a cut below MIN_NOTIONAL is rejected by the venue; the ladder retries it every anchor")

shutil.rmtree(_tmp, ignore_errors=True)
print(f"\n  {N[0]} checks run")
print(f"\n{'ALL PASS' if not FAILS else 'FAILURES: ' + str(FAILS)}")
sys.exit(0 if not FAILS else 1)
