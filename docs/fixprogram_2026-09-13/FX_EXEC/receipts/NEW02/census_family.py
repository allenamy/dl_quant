import json, collections
CEN="/Users/haosiyu/cc_tmp/fx_exec_census_new02"
for day in ("20260909","20260912"):
    print("="*72); print("DAY", day)
    O=[json.loads(l) for l in open(f"{CEN}/{day}/orders.jsonl",encoding="utf-8") if l.strip()]
    F=[json.loads(l) for l in open(f"{CEN}/{day}/fills.jsonl",encoding="utf-8") if l.strip()]
    # requoted maker order rows (attempt 2) and whether they filled
    mk2=[o for o in O if o.get("order_type")=="maker" and int(o.get("attempt_idx") or 1)==2]
    filled2=[o for o in mk2 if abs(float(o.get("filled_notional") or 0.0))>0]
    print(f"  maker attempt-2 ORDER rows: {len(mk2)}; of which filled_notional!=0: {len(filled2)}")
    for o in filled2[:6]:
        print("     ", o["symbol"], o["rebalance_id"], "filled", o.get("filled_notional"), o.get("terminal_reason"))
    # do their fills exist, and what attempt_idx do they carry?
    keyO={(o["rebalance_id"],o["symbol"]) for o in filled2}
    hit=[f for f in F if (f.get("rebalance_id"),f.get("symbol")) in keyO and f.get("order_type")=="maker"]
    print(f"  FILL rows on those (rid,symbol) with order_type=maker: {len(hit)}; attempt_idx: {dict(collections.Counter(f.get('attempt_idx') for f in hit))}")
    # the orders-side join dict, exactly as the research devices build it
    PXkeys={(o["rebalance_id"],o["symbol"],o["order_type"],int(o.get("attempt_idx") or 1)) for o in O}
    miss=collections.Counter()
    for f in F:
        k=(f.get("rebalance_id"),f.get("symbol"),f.get("order_type"),int(f.get("attempt_idx") or 1))
        if k not in PXkeys: miss[f.get("order_type")]+=1
    print("  FILL rows whose (rid,sym,order_type,attempt_idx) key has NO order row:", dict(miss))
