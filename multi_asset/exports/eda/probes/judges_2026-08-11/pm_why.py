import sys, os, json
from collections import Counter
LIVE = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/engine/live"
ROOT = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/live/pilot_log"
sys.path.insert(0, LIVE)
import pilot_log as PL
data = PL.read_range(ROOT, PL.available_days(ROOT))
orders = data["orders"]
print("total order rows:", len(orders), " days:", len(PL.available_days(ROOT)))
fn = [o.get("filled_notional") for o in orders]
print("filled_notional  None:", sum(1 for x in fn if x is None),
      " ==0:", sum(1 for x in fn if x is not None and float(x) == 0),
      " >0:", sum(1 for x in fn if x is not None and float(x) > 0),
      " <0:", sum(1 for x in fn if x is not None and float(x) < 0))
print("sides on FILLED rows:",
      Counter(o.get("side") for o in orders if o.get("filled_notional") not in (None,)
              and float(o["filled_notional"]) != 0))
print("terminal_reason on rows with negative filled_notional:",
      Counter(o.get("terminal_reason") for o in orders
              if o.get("filled_notional") is not None and float(o["filled_notional"]) < 0))
