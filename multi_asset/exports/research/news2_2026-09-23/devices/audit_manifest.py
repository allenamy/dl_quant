import json
W = "/dev/shm/news2_2026-09-23"
m = json.load(open(f"{W}/receipts/P5_DEPLOY_MANIFEST.json"))
print("=== lead req 2: the three required fields ===")
for k in ("VERDICT", "USER_OVERRIDE", "seed"):
    print("  ", k, "=", m.get(k))
print("   export_status =", str(m.get("export_status"))[:140])
print("   user_override =", m.get("user_override"))
print("=== wording audit: every occurrence of PASS / admitted / certified ===")


def walk(o, p=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from walk(v, p + "." + str(k))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from walk(v, p + "[" + str(i) + "]")
    else:
        yield p, o


hits = [(p, v) for p, v in walk(m)
        if any(w in str(p) + str(v) for w in ("PASS", "admitted", "certified", "BOUND"))]
for p, v in hits:
    print("  ", p, "=", str(v)[:80])
print("=== exported_files (full shas) ===")
for f in m["exported_files"]:
    print("  ", f["name"].ljust(22), f["sha256"], f["bytes"], "bytes")
