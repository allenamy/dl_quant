import json, collections
CEN="/Users/haosiyu/cc_tmp/fx_exec_census_new02"
for day in ("20260909","20260912"):
    fills=[json.loads(l) for l in open(f"{CEN}/{day}/fills.jsonl",encoding="utf-8") if l.strip()]
    ff=[f for f in fills if f.get("order_type")=="protective_flatten"]
    def prov(f):
        return ("rebuilt_from_venue" if f.get("rebuilt_from_venue") else
                "backfilled_utc" if f.get("backfilled_utc") else "inline")
    c=collections.Counter((prov(f), f.get("attempt_idx"), f.get("supersedes_trade_id") is not None) for f in ff)
    print(day, "(provenance, attempt_idx, is_supersede) -> n")
    for k in sorted(c, key=str): print("   ", k, c[k])
