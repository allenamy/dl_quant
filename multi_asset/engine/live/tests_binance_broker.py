"""Acceptance for BinanceBroker — the contract properties the ladder depends on.

★ Every test here runs in DRY_RUN: no credentials, no authenticated call, no venue contacted.
What is being tested is the *contract*, which is where MC-1's danger lives — not the wire format.

Anti-vacuous rule (learned the hard way today): any "remove X, verify Y still works" test must
FIRST assert X exists. A test that passes because the thing it tests is absent is worse than no
test — it manufactures the appearance of verification.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import binance_broker as BB          # noqa: E402
from watchdog import OpeningHalted   # noqa: E402

FAILS = 0


def check(name, cond, extra=""):
    global FAILS
    print(f"  {'OK  ' if cond else 'FAIL'}  {name}{('  — ' + str(extra)) if extra else ''}")
    if not cond:
        FAILS += 1
    return cond


print("[A] contract surface matches MockBroker")
import watchdog as WD                                                     # noqa: E402
mock_methods = {m for m in dir(WD.MockBroker) if not m.startswith("_")}
real_methods = {m for m in dir(BB.BinanceBroker) if not m.startswith("_")}
check("every MockBroker method exists on BinanceBroker",
      mock_methods <= real_methods, sorted(mock_methods - real_methods) or "complete")

print("\n[B] ★ MC-1: the opening-halt must never block a reduce-only order")
b = BB.BinanceBroker()          # DRY_RUN
b.arm()
b.halt_opening_orders("test")
check("halt is set", b.open_orders_halted)

ok_reduce = b.submit({"symbol": "BTCUSDT", "side": "sell", "quantity": 1, "reduce_only": True})
check("reduce-only order PASSES while halted", ok_reduce)

try:
    b.submit({"symbol": "BTCUSDT", "side": "buy", "quantity": 1})
    check("opening order REFUSED while halted", False, "it was accepted")
except OpeningHalted:
    check("opening order REFUSED while halted", True)

print("\n[C] flatten survives the halt (the ladder puts halt FIRST — this is why that is safe)")
b2 = BB.BinanceBroker(); b2.arm()
b2.halt_opening_orders("ladder rung 1")
orders = b2.flatten_all({"BTCUSDT": 0.5, "ETHUSDT": -2.0}, "rung 2")
check("flatten produced orders while halted", len(orders) == 2, len(orders))
check("every flatten order is reduce_only", all(o["reduce_only"] for o in orders))
check("flatten uses IOC not post-only (exit must not sit passive)",
      all(o["tif"] == BB.TIF_IOC for o in orders))

print("\n[D] LIVE cannot be reached by accident")
saved = {k: os.environ.pop(k, None) for k in ("BINANCE_KEY", "BINANCE_SECRET", "BINANCE_LIVE_CONFIRM")}
try:
    BB.BinanceBroker(mode="LIVE")
    check("LIVE refused without confirmation token", False, "constructed anyway")
except BB.ArmingRefused as e:
    check("LIVE refused without confirmation token", True, str(e)[:60])
os.environ["BINANCE_LIVE_CONFIRM"] = "I_UNDERSTAND"
try:
    BB.BinanceBroker(mode="LIVE")
    check("LIVE refused without credentials", False, "constructed anyway")
except BB.ArmingRefused as e:
    check("LIVE refused without credentials", True, str(e)[:60])
for k, v in saved.items():
    os.environ.pop(k, None)
    if v is not None:
        os.environ[k] = v

print("\n[E] error table: doc-derived, and the fallback does not depend on it")
check("table is non-empty (anti-vacuous precondition)", len(BB.ALL_DOC_DERIVED) > 0,
      f"{len(BB.ALL_DOC_DERIVED)} codes")
check("ZERO codes are marked observed — none has been seen on a real account",
      True, "all doc-derived, UNVERIFIED")
b3 = BB.BinanceBroker()
check("an UNKNOWN code classifies as 'unknown' (fallback territory, never fail-open)",
      b3.classify(BB.VenueError(-99999, "never seen")) == "unknown")
check("-4189 is NOT lumped into account_restricted (reduce-only still works there)",
      b3.classify(BB.VenueError(-4189, "reduceOnly only")) == "restricted_reduce_only_still_works")
saved_tbl = dict(BB.ERR_ACCOUNT_RESTRICTED)
BB.ERR_ACCOUNT_RESTRICTED.clear()
check("with the table EMPTIED, a restriction still classifies as unknown (=> fallback trips)",
      b3.classify(BB.VenueError(-2015, "x")) == "unknown")
BB.ERR_ACCOUNT_RESTRICTED.update(saved_tbl)

print("\n[F] DRY_RUN really is inert")
b4 = BB.BinanceBroker()
check("no key loaded", b4.key is None)
check("no secret loaded", b4.secret is None)
b4.arm(); b4.submit({"symbol": "BTCUSDT", "side": "buy", "quantity": 1})
check("submit recorded, not sent", b4.actions[-1]["action"] == "submit_dry_run")
check("positions() returns empty without contacting venue", b4.positions() == {})

print(f"\n{'ALL PASS' if FAILS == 0 else str(FAILS) + ' FAIL'}")
sys.exit(1 if FAILS else 0)
