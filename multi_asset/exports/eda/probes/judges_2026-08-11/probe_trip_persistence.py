"""Does a watchdog trip survive to the NEXT anchor? Empirical, no production writes."""
import json, os, sys, tempfile
REPO = os.path.expanduser("~/dl_quant_live")
sys.path.insert(0, os.path.join(REPO, "live"))
sys.path.insert(0, os.path.join(REPO, "scheduler"))
tmp = tempfile.mkdtemp()

# 1. Simulate anchor N having TRIPPED: write the exact state watchdog writes.
wdir = os.path.join(tmp, "watchdog"); os.makedirs(wdir)
json.dump({"reduce_only": True, "open_orders_halted": True,
           "tripped_at": "2026-07-25T18:46:36Z", "reason": "§4-5c account anomaly",
           "resume_requires": "a deliberate manual action"},
          open(os.path.join(wdir, "state.json"), "w"))

# 2. Anchor N+1 = a FRESH process. What does the broker init to?
from binance_broker import BinanceBroker
b = BinanceBroker(mode="DRY_RUN")
print(f"fresh broker open_orders_halted = {b.open_orders_halted}")
print(f"fresh broker reduce_only        = {getattr(b,'reduce_only',None)}")

# 3. Does the pre-trade gate consult the watchdog state at all?
os.environ["LIVE_KILL_SWITCH"] = os.path.join(tmp, "KILL_SWITCH.json")   # absent => not killed
src = open(os.path.join(REPO, "scheduler", "anchor_loop.py")).read()
print(f"anchor_loop mentions watchdog state.json : {'watchdog' in src and 'state.json' in src}")
print(f"anchor_loop mentions tripped_at          : {'tripped_at' in src}")
print(f"anchor_loop KILL path                    : state/KILL_SWITCH.json")
print(f"watchdog trip writes                     : state/watchdog/state.json")
print()
readers = []
for d in ("live", "scheduler", "ops"):
    for f in os.listdir(os.path.join(REPO, d)):
        if not f.endswith(".py") or f.startswith("tests_"): continue
        t = open(os.path.join(REPO, d, f)).read()
        if "watchdog" in t and "state.json" in t:
            readers.append(f"{d}/{f}")
print(f"non-test files touching watchdog state.json: {readers}")
