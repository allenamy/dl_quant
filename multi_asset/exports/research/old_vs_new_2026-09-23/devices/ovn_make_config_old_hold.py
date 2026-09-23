#!/usr/bin/env python3
"""ovn_make_config_old_hold.py — AMENDMENT 1 (70adc6cac / 73336df6) run configuration of arm OLD_HOLD, derived from the frozen RUN_CONFIG_OVN_OLD
(1c0f7881) by copy. Changes ONLY: labels (config / status / created_utc / object / pending / ovn), per run arm / tag / role / targets.arm /
targets.sources (the ovn_old_hold.py TARGETS_OLD_HOLD npz + receipt, shas pinned), objb_lineage -> old_hold_lineage, and the lit run is dropped
(the amendment rewrites the scaled reading only; lit is report-only and OLD's lit is unchanged). The leaf diff is taken against OVN_OLD with its
lit run removed and asserted against the same allowed set as NEW vs OLD; every setting is byte-identical.
usage: python -B ovn_make_config_old_hold.py PATH,HOME,LC_CTYPE <out_config.json> <targets_receipt.json> <diff_receipt.json>
"""
import os, sys, json, time, hashlib, re

WL = set(sys.argv[1].split(",")); extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
OUTC, TR, DIFF = sys.argv[2:5]
NR = "/workspace/old_vs_new_2026-09-23"; OLDC = f"{NR}/RUN_CONFIG_OVN_OLD_2026-09-23.json"; OLDC_SHA = "1c0f788193a797955407a50528cf5755c009da0d47821e6725591758d67f9e8d"
TNPZ = "/dev/shm/ovn_2026-09-23/targets/TARGETS_OLD_HOLD.npz"
AMD = {"path": "docs/AMENDMENT_1_old_vs_new_models_same_engine_2026-09-23.md", "commit": "70adc6cac", "sha256": "73336df6d4d5568bffff6148d9d63b3139d7279407958537f1d93c4d5d18a854"}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


assert sha(OLDC) == OLDC_SHA, "OVN_OLD config sha"
O = json.load(open(OLDC)); R = json.load(open(TR))
assert R["arm"] == "OLD_HOLD" and sha(TNPZ) == R["targets_npz_sha256"], "OLD_HOLD targets receipt"
Oref = json.loads(json.dumps(O)); Oref["runs"] = [r for r in Oref["runs"] if r["book"] == "scaled"]
N = json.loads(json.dumps(Oref)); NOW = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
N["config"] = "RUN_CONFIG_OVN_OLD_HOLD_2026-09-23"
N["status"] = "FROZEN before any number of the OLD-vs-NEW comparison (OVN Stage 1, AMENDMENT 1 arm OLD_HOLD); settings byte-identical to RUN_CONFIG_OVN_OLD"
N["created_utc"] = NOW
N["object"] = "OVN Stage 1 AMENDMENT 1 arm OLD_HOLD: certified object B A0_main with every scaled King-fallback (kind 1) anchor rewritten as HOLD (ovn_old_hold.py)"
N["pending"] = {"(a) targets": "filled: TARGETS_OLD_HOLD (RT1/RT2/RT3 PASS)", "(b) the other arms": "RUN_CONFIG_OVN_OLD / RUN_CONFIG_OVN_NEW_s42 / RUN_CONFIG_OVN_NEW_s2027"}
N["ovn"] = dict(O["ovn"], role="OLD_HOLD arm (AMENDMENT 1)", amendment_1=AMD)
N.pop("objb_lineage", None)
N["old_hold_lineage"] = {"targets_receipt": {"path": TR, "sha256": sha(TR)}, "source": R["source"], "rewritten_anchors_total": R["rewritten_anchors_total"]}
for r in N["runs"]:
    r["arm"] = "OVN_OLD_HOLD"; r["tag"] = "OVN_OLD_HOLD|" + r["tag"].split("|", 1)[1]; r["role"] = r["role"].replace("in-service recipe (object B A0)", "OLD_HOLD (A0 with King fallback -> HOLD)")
    r["targets"]["arm"] = "OLD_HOLD"; r["targets"]["sources"] = [{"npz": TNPZ, "npz_sha256": R["targets_npz_sha256"], "receipt": TR, "receipt_sha256": sha(TR)}]


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


la, lb = leaves(Oref), leaves(N); ks = sorted(set(la) | set(lb))
d = [{"leaf": k, "a": la.get(k, "<absent>"), "b": lb.get(k, "<absent>")} for k in ks if la.get(k, "<absent>") != lb.get(k, "<absent>")]
ALLOWED = [r"^config$", r"^status$", r"^created_utc$", r"^object$", r"^pending(\.|$)", r"^ovn(\.|$)", r"^objb_lineage(\.|$)", r"^old_hold_lineage(\.|$)",
           r"^runs\[\d+\]\.(arm|tag|role)$", r"^runs\[\d+\]\.targets\.arm$", r"^runs\[\d+\]\.targets\.sources(\[\d+\]\.(npz|npz_sha256|receipt|receipt_sha256))?$"]
bad = [x["leaf"] for x in d if not any(re.search(p, x["leaf"]) for p in ALLOWED)]
assert not bad, f"settings would differ: {bad[:10]}"
assert not [k for k, v in lb.items() if v == "PENDING"]
json.dump(N, open(OUTC, "w"), indent=1, ensure_ascii=False)
rec = {"device": "ovn_make_config_old_hold.py", "self_sha256": sha(os.path.abspath(__file__)), "utc": NOW, "amendment_1": AMD, "base": {"path": OLDC, "sha256": OLDC_SHA},
       "dropped_runs_from_base": [r["tag"] for r in O["runs"] if r["book"] != "scaled"], "config": {"path": OUTC, "sha256": sha(OUTC), "runs": [r["tag"] for r in N["runs"]]},
       "diff_vs_OVN_OLD_without_lit": d, "allowed": ALLOWED}
json.dump(rec, open(DIFF, "w"), indent=1, ensure_ascii=False)
print("OVN_MAKE_CONFIG_OLD_HOLD VERDICT=PASS", sha(OUTC)[:16], "runs", rec["config"]["runs"], "diff_leaves", len(d), flush=True)
