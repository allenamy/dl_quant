import json, collections, os
CEN="/Users/haosiyu/cc_tmp/fx_exec_census_new02"
day="20260909"
O=[json.loads(l) for l in open(f"{CEN}/{day}/orders.jsonl",encoding="utf-8") if l.strip()]
F=[json.loads(l) for l in open(f"{CEN}/{day}/fills.jsonl",encoding="utf-8") if l.strip()]
PXkeys={(o["rebalance_id"],o["symbol"],o["order_type"],int(o.get("attempt_idx") or 1)) for o in O}
miss=[f for f in F if (f.get("rebalance_id"),f.get("symbol"),f.get("order_type"),int(f.get("attempt_idx") or 1)) not in PXkeys]
print("n miss", len(miss))
print("by rid:", dict(collections.Counter(f.get("rebalance_id") for f in miss)))
rids_in_orders=collections.Counter(o["rebalance_id"] for o in O)
print("those rids' order-row counts in THIS day's orders.jsonl:",
      {r: rids_in_orders.get(r,0) for r in {f.get("rebalance_id") for f in miss}})
# is the (rid,symbol) present at all, at any attempt/order_type?
pres={(o["rebalance_id"],o["symbol"]) for o in O}
print("miss rows whose (rid,symbol) IS present in orders:", sum(1 for f in miss if (f.get("rebalance_id"),f.get("symbol")) in pres))
for f in miss[:3]:
    k=(f.get("rebalance_id"),f.get("symbol"))
    print("  sample miss:", k, f.get("order_type"), f.get("attempt_idx"),
          "| order rows for that (rid,sym):", [(o.get("order_type"),o.get("attempt_idx"),o.get("terminal_reason")) for o in O if (o["rebalance_id"],o["symbol"])==k])
