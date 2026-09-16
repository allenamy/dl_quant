import json, collections
CEN="/Users/haosiyu/cc_tmp/fx_exec_census_new02"
for day in ("20260909","20260912"):
    O=[json.loads(l) for l in open(f"{CEN}/{day}/orders.jsonl",encoding="utf-8") if l.strip()]
    fo=[o for o in O if o.get("order_type")=="protective_flatten"]
    print(day, "flatten order rows", len(fo),
          "| with client_id:", sum(1 for o in fo if o.get("client_id")),
          "| client_id_dropped:", sum(1 for o in fo if o.get("client_id_dropped")))
    ex=[o.get("client_id") for o in fo if o.get("client_id")][:3]
    print("   sample client_ids:", ex, "| rid:", fo[0].get("rebalance_id") if fo else None)
    # do the client-id suffixes look like the attempt (1) or like a process-wide seq?
    sfx=[str(o.get("client_id","")).rsplit("-",1)[-1] for o in fo if o.get("client_id")]
    c=collections.Counter(sfx)
    print("   suffix distinct values:", len(c), "min/max:", (min(sfx,key=int) if sfx else None), (max(sfx,key=int) if sfx else None))
