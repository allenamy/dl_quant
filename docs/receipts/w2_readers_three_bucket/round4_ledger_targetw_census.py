import glob, json, math, os, collections, sys
ROOT = sys.argv[1]
c = collections.Counter(); skipped_int = collections.Counter(); tr = collections.Counter()
for p in sorted(glob.glob(os.path.join(ROOT, "*", "orders.jsonl"))):
    for l in open(p):
        if not l.strip(): continue
        r = json.loads(l)
        v = r.get("target_w")
        s = "absent" if "target_w" not in r else "None" if v is None else ("nonfinite" if not math.isfinite(float(v)) else "finite")
        c[(r.get("order_type"), s)] += 1
        if str(r.get("terminal_reason")) == "skipped_min_notional":
            iv = r.get("intended_notional")
            skipped_int[(r.get("order_type"), "None" if iv is None else "finite")] += 1
print("target_w by order_type:", dict(c))
print("skipped_min_notional intended_notional:", dict(skipped_int))
