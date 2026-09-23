import json, re
def leaves(o, p=""):
    if isinstance(o, dict):
        out = {}
        for k, v in o.items(): out.update(leaves(v, f"{p}.{k}" if p else k))
        return out if o else {p: {}}
    if isinstance(o, list):
        out = {}
        for i, v in enumerate(o): out.update(leaves(v, f"{p}[{i}]"))
        return out if o else {p: []}
    return {p: o}
def diff(a, b):
    la, lb = leaves(a), leaves(b); ks = sorted(set(la) | set(lb))
    return [k for k in ks if la.get(k, "<absent>") != lb.get(k, "<absent>")]
ALLOWED = [r"^config$", r"^status$", r"^created_utc$", r"^object$", r"^pending(\.|$)", r"^ovn(\.|$)", r"^objb_lineage(\.|$)", r"^new_lineage(\.|$)",
           r"^runs\[\d+\]\.(arm|tag|role)$", r"^runs\[\d+\]\.targets\.arm$", r"^runs\[\d+\]\.targets\.sources(\[\d+\]\.(npz|npz_sha256|receipt|receipt_sha256))?$",
           r"^paths\.pod_root$"]
N = "/dev/shm/news_2026-09-23/configs"; S1 = "/workspace/old_vs_new_2026-09-23"
OLD = f"{S1}/RUN_CONFIG_OVN_OLD_2026-09-23.json"
for tag, b in (("NEWS_s42", f"{N}/RUN_CONFIG_NEWS_s42_2026-09-23.json"),
               ("NEWS_s2027", f"{N}/RUN_CONFIG_NEWS_s2027_2026-09-23.json"),
               ("NEWS_s42X", f"{N}/RUN_CONFIG_NEWS_s42X_2026-09-23.json"),
               ("NEWS_s2027X", f"{N}/RUN_CONFIG_NEWS_s2027X_2026-09-23.json")):
    A = json.load(open(OLD)); B = json.load(open(b)); d = diff(A, B)
    bad = [x for x in d if not any(re.search(p, x) for p in ALLOWED)]
    print(f"{tag:12s} vs OVN_OLD: differing leaves {len(d):3d} | outside ALLOWED: {bad[:6]}")
C = json.load(open(f"{N}/RUN_CONFIG_NEWS_s42_2026-09-23.json"))
print("runs:", [(r["arm"], r["tag"]) for r in C["runs"]])
print("role[0]:", C["runs"][0]["role"])
print("pod_root:", C["paths"]["pod_root"])
import re as _re
for r in C["runs"]:
    new = _re.sub(r"NEW_S arm NEWS_s\d+", "FRESH arm FRESH_s42", r["role"])
    print("relabel ok:", ("FRESH arm FRESH_s42" in new and "NEWS_s" not in new), "|", new[:70])
