import json, collections, sys, os
CEN = "/Users/haosiyu/cc_tmp/fx_exec_census_new02"
for day in sorted(os.listdir(CEN)):
    d = os.path.join(CEN, day)
    if not os.path.isdir(d):
        continue
    print("="*78)
    print("DAY", day)
    orders = [json.loads(l) for l in open(os.path.join(d, "orders.jsonl"), encoding="utf-8") if l.strip()]
    fills  = [json.loads(l) for l in open(os.path.join(d, "fills.jsonl"),  encoding="utf-8") if l.strip()]
    print("  n_order_rows", len(orders), " n_fill_rows", len(fills))
    # --- order rows, by order_type x attempt_idx
    print("  ORDER rows  order_type x attempt_idx:")
    c = collections.Counter((o.get("order_type"), o.get("attempt_idx")) for o in orders)
    for k in sorted(c, key=lambda x: (str(x[0]), str(x[1]))):
        print("     ", k, c[k])
    print("  FILL rows   order_type x attempt_idx:")
    c = collections.Counter((f.get("order_type"), f.get("attempt_idx")) for f in fills)
    for k in sorted(c, key=lambda x: (str(x[0]), str(x[1]))):
        print("     ", k, c[k])
    # --- the flatten batches
    flat_o = [o for o in orders if o.get("order_type") == "protective_flatten"]
    flat_f = [f for f in fills  if f.get("order_type") == "protective_flatten"]
    print("  flatten ORDER rows", len(flat_o), " flatten FILL rows", len(flat_f))
    for rid in sorted({o.get("rebalance_id") for o in flat_o} | {f.get("rebalance_id") for f in flat_f}):
        oo = [o for o in flat_o if o.get("rebalance_id") == rid]
        ff = [f for f in flat_f if f.get("rebalance_id") == rid]
        print(f"    rid={rid}: orders={len(oo)} attempts={dict(collections.Counter(o.get('attempt_idx') for o in oo))}"
              f" | fills={len(ff)} attempts={dict(collections.Counter(f.get('attempt_idx') for f in ff))}")
        # per-symbol: which attempt actually filled, per the ORDER rows
        filled_att = collections.Counter()
        for o in oo:
            if o.get("terminal_reason") in ("filled", "filled_amount_unknown"):
                filled_att[o.get("attempt_idx")] += 1
        print(f"       ORDER rows with a fill, by attempt: {dict(filled_att)}")
