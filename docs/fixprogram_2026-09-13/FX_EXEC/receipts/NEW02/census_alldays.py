import json, os, collections
PL="/Users/haosiyu/dl_quant_live/state/live/pilot_log"
tot=collections.Counter(); print(f"{'day':>10} {'flat_ord':>9} {'ord_att':>12} {'flat_fill':>10} {'fill_att':>12} {'join_miss':>10}")
for d in sorted(os.listdir(PL)):
    if not (len(d)==8 and d.isdigit()): continue
    op, fp = f"{PL}/{d}/orders.jsonl", f"{PL}/{d}/fills.jsonl"
    if not (os.path.exists(op) and os.path.exists(fp)): continue
    O=[json.loads(l) for l in open(op,encoding="utf-8") if l.strip()]
    F=[json.loads(l) for l in open(fp,encoding="utf-8") if l.strip()]
    fo=[o for o in O if o.get("order_type")=="protective_flatten"]
    ff=[f for f in F if f.get("order_type")=="protective_flatten"]
    if not (fo or ff): continue
    keys={(o["rebalance_id"],o["symbol"],o["order_type"],int(o.get("attempt_idx") or 1)) for o in O}
    miss=sum(1 for f in ff if (f.get("rebalance_id"),f.get("symbol"),f.get("order_type"),int(f.get("attempt_idx") or 1)) not in keys)
    tot["ord"]+=len(fo); tot["fill"]+=len(ff); tot["miss"]+=miss
    print(f"{d:>10} {len(fo):>9} {str(dict(collections.Counter(o.get('attempt_idx') for o in fo))):>12} "
          f"{len(ff):>10} {str(dict(collections.Counter(f.get('attempt_idx') for f in ff))):>12} {miss:>10}")
print("TOTAL flatten order rows", tot["ord"], "flatten fill rows", tot["fill"], "join misses", tot["miss"])
