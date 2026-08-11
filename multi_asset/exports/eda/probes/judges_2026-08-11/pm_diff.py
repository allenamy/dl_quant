import json
d = json.load(open("/tmp/pm_diff.json")); old, new = d["old"], d["new"]

def flat(o, p=""):
    out = {}
    if isinstance(o, dict):
        for k, v in o.items(): out.update(flat(v, (p + "." + k) if p else k))
    elif isinstance(o, list):
        out[p] = "<list n=%d>" % len(o)
    else:
        out[p] = o
    return out

fo, fn = flat(old), flat(new)
keys = sorted(set(fo) | set(fn))
same = 0
print("%-52s %26s %26s" % ("key", "OLD cfd1de1b", "NEW 9a033684"))
print("-" * 108)
for k in keys:
    a, b = fo.get(k, "<absent>"), fn.get(k, "<absent>")
    if a == b:
        same += 1; continue
    print("%-52s %26s %26s" % (k, str(a)[:26], str(b)[:26]))
print("-" * 108)
print("identical leaves: %d / %d   differing or added: %d" % (same, len(keys), len(keys) - same))
