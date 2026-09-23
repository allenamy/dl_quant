#!/usr/bin/env python3
"""ovn_make_configs.py — the frozen run configurations of the OLD-vs-NEW comparison (prereg §1.2, §1.7 item 5), derived from the CERTIFIED
configs by copy, with a leaf-level diff that is asserted before anything is written.
  RUN_CONFIG_OVN_OLD      = certified RUN_CONFIG_main_A0_2026-09-19.json (7b6dca2c) with ONLY: config / status / created_utc labels,
                            paths.pod_root (run outputs on /dev/shm: the /workspace volume is at its quota) and a new 'ovn' provenance block.
                            Run tags are unchanged, so every path file can be compared byte for byte with the certified runs.
  RUN_CONFIG_OVN_NEW_s{42,2027} = RUN_CONFIG_OVN_OLD with ONLY: labels (config / status / created_utc / object / pending / ovn), and per run:
                            arm, tag, role, targets.arm, targets.sources (the adapter's TARGETS_NEW_s* npz + receipt, shas pinned);
                            objb_lineage (an OLD-only provenance block) replaced by new_lineage. Every setting (window, seeds, gross, chase,
                            decision / stop offsets, events, policies, cost cells, calibration, pins, launch) is byte-identical.
  RUN_CONFIG_OVN_NEW_s{42,2027}X = certified RUN_CONFIG_main_A0ext_2026-09-20.json (acafccc6), scaled main run only (describe-only extension
                            2026-08-31T04Z..09-18T20Z), same substitutions; OLD for that segment = the certified OBJB_A0X_scaled run.
Refuses if any differing leaf falls outside the allowed set, or a config contains "PENDING".
usage: python -B ovn_make_configs.py PATH,HOME,LC_CTYPE <out_dir> <adapter_receipt_s42> <adapter_receipt_s2027> <diff_receipt.json>
"""
import os, sys, json, time, hashlib, re

WL = set(sys.argv[1].split(",")); extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
OUTD, AR42, AR2027, DIFF = sys.argv[2:6]
BT = "/workspace/baseline_tables_2026-09-19"; NR = "/workspace/old_vs_new_2026-09-23"; POD_ROOT = "/dev/shm/ovn_2026-09-23"
CERT = {"main": (f"{BT}/RUN_CONFIG_main_A0_2026-09-19.json", "7b6dca2c48feda294676ab5ce46b748c71ab87103cc64ead5be7957fe5bbfe93"),
        "ext": (f"{BT}/RUN_CONFIG_main_A0ext_2026-09-20.json", "acafccc6b3b7a1e15ab502b92b5bd78603da1befa2d2b10bf063fc4937f9ab3b")}
PREREG = {"path": "docs/PREREG_old_vs_new_models_same_engine_2026-09-23.md", "commit": "8530d2b7f", "sha256": "1217d786b29cf8bcb37f4aa86f2e9862bb278f7c1a91cc9ac58ed9376b9a31b4"}
NOW = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


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
    return [{"leaf": k, "a": la.get(k, "<absent>"), "b": lb.get(k, "<absent>")} for k in ks if la.get(k, "<absent>") != lb.get(k, "<absent>")]


def pending(o):
    return [k for k, v in leaves(o).items() if v == "PENDING"]


ALLOWED_OLD_VS_CERT = [r"^config$", r"^status$", r"^created_utc$", r"^paths\.pod_root$", r"^ovn(\.|$)"]
ALLOWED_NEW_VS_OLD = [r"^config$", r"^status$", r"^created_utc$", r"^object$", r"^pending(\.|$)", r"^ovn(\.|$)", r"^objb_lineage(\.|$)", r"^new_lineage(\.|$)",
                      r"^runs\[\d+\]\.(arm|tag|role)$", r"^runs\[\d+\]\.targets\.arm$", r"^runs\[\d+\]\.targets\.sources(\[\d+\]\.(npz|npz_sha256|receipt|receipt_sha256))?$"]


def check(d, allowed, what):
    bad = [x["leaf"] for x in d if not any(re.search(p, x["leaf"]) for p in allowed)]
    assert not bad, f"{what}: leaves outside the allowed set (settings would differ): {bad[:10]}"


C = {}
for k, (p, s) in CERT.items():
    assert sha(p) == s, f"certified config sha {p}"; C[k] = json.load(open(p))
AR = {}
for seed, p in (("42", AR42), ("2027", AR2027)):
    R = json.load(open(p)); assert R["arm"] == f"NEW_s{seed}" and R["roundtrip"]["scaled"]["bitwise_equal"] and R["roundtrip"]["lit"]["bitwise_equal"], "adapter receipt"
    AR[seed] = (p, R)
os.makedirs(OUTD, exist_ok=True)
docs = {}; receipts = {"device": "ovn_make_configs.py", "self_sha256": sha(os.path.abspath(__file__)), "utc": NOW, "prereg": PREREG, "certified": {k: {"path": p, "sha256": s} for k, (p, s) in CERT.items()},
                       "pod_root": POD_ROOT, "pod_root_reason": "/workspace volume returned EDQUOT (Disk quota exceeded) at 06:03Z with ~200 MB headroom; one run = ~350 MB of path files", "configs": {}, "diffs": {}}


def ovn_block(base_name, base_sha, role):
    return {"prereg": PREREG, "derived_from": {"config": base_name, "sha256": base_sha}, "role": role, "device": "ovn_make_configs.py", "pod_root_reason": receipts["pod_root_reason"]}


def old_cfg(kind):
    O = json.loads(json.dumps(C[kind])); p, s = CERT[kind]
    O["config"] = f"RUN_CONFIG_OVN_OLD{'X' if kind == 'ext' else ''}_2026-09-23"
    O["status"] = "FROZEN before any number of the OLD-vs-NEW comparison (OVN Stage 1); a re-run of the certified config with only labels and the output root changed"
    O["created_utc"] = NOW; O["paths"]["pod_root"] = POD_ROOT; O["ovn"] = ovn_block(os.path.basename(p), s, "OLD arm (certified object B A0, scaled main reading)")
    return O


def new_cfg(O, seed, kind):
    N = json.loads(json.dumps(O)); p, R = AR[seed]; arm = f"NEW_s{seed}"; run_arm = f"OVN_NEW_s{seed}{'X' if kind == 'ext' else ''}"
    tnpz = R["_npz_path"]; assert sha(tnpz) == R["targets_npz_sha256"], "adapter npz sha vs its receipt"
    N["config"] = f"RUN_CONFIG_OVN_NEW_s{seed}{'X' if kind == 'ext' else ''}_2026-09-23"
    N["status"] = f"FROZEN before any number of the OLD-vs-NEW comparison (OVN Stage 1); arm {arm}; settings byte-identical to RUN_CONFIG_OVN_OLD{'X' if kind == 'ext' else ''}"
    N["object"] = f"OVN Stage 1 arm {arm}: researcher corrected_combo_v1d combo_s{seed} (scaled_diagnostic = scaled reading, literal = lit reading), through ovn_adapter.py"
    N["pending"] = {"(a) targets": f"filled: TARGETS_{arm} (adapter round-trip bitwise PASS)", "(b) the other arm": "RUN_CONFIG_OVN_OLD (re-run of the certified A0 config)"}
    N["ovn"] = dict(O["ovn"], role=f"NEW arm {arm}")
    N.pop("objb_lineage", None)
    N["new_lineage"] = {"arm": arm, "adapter_receipt": {"path": p, "sha256": sha(p)}, "new_target_receipt": R["adapter"]["new_receipt"], "sources": R["adapter"]["sources"]}
    for r in N["runs"]:
        r["arm"] = run_arm; r["tag"] = run_arm + "|" + r["tag"].split("|", 1)[1]
        r["role"] = r["role"].replace("in-service recipe (object B A0)", f"NEW arm {arm}")
        r["targets"]["arm"] = arm
        r["targets"]["sources"] = [{"npz": tnpz, "npz_sha256": R["targets_npz_sha256"], "receipt": p, "receipt_sha256": sha(p)}]
    return N


for seed in ("42", "2027"):
    p, R = AR[seed]; R["_npz_path"] = f"{POD_ROOT}/targets/TARGETS_NEW_s{seed}.npz"
OLD = old_cfg("main"); OLDX = old_cfg("ext")
OLDX["runs"] = [r for r in OLDX["runs"] if r["book"] == "scaled" and not r.get("cost_cell")]    # describe-only extension: the main reading only
d = diff(C["main"], OLD); check(d, ALLOWED_OLD_VS_CERT, "OVN_OLD vs certified A0"); receipts["diffs"]["OVN_OLD_vs_certified_A0"] = d
docs["RUN_CONFIG_OVN_OLD_2026-09-23.json"] = OLD
for seed in ("42", "2027"):
    N = new_cfg(OLD, seed, "main"); d = diff(OLD, N); check(d, ALLOWED_NEW_VS_OLD, f"OVN_NEW_s{seed} vs OVN_OLD"); receipts["diffs"][f"OVN_NEW_s{seed}_vs_OVN_OLD"] = d
    docs[f"RUN_CONFIG_OVN_NEW_s{seed}_2026-09-23.json"] = N
    NX = new_cfg(OLDX, seed, "ext"); d = diff(OLDX, NX); check(d, ALLOWED_NEW_VS_OLD, f"OVN_NEW_s{seed}X vs OVN_OLDX"); receipts["diffs"][f"OVN_NEW_s{seed}X_vs_OVN_OLDX(scaled run only)"] = d
    docs[f"RUN_CONFIG_OVN_NEW_s{seed}X_2026-09-23.json"] = NX
receipts["ext_note"] = ("OVN_OLDX is NOT run: the extension segment's OLD reading is the certified OBJB_A0X_scaled_rule_raw_UAFE run (same settings; certified A0ext config "
                        "acafccc6). Diff OVN_OLDX vs certified A0ext = labels + pod_root + the dropped non-main runs.")
dx = diff(C["ext"], OLDX); receipts["diffs"]["OVN_OLDX_vs_certified_A0ext"] = {"n_leaves": len(dx), "non_run_leaves": [x for x in dx if not x["leaf"].startswith("runs[")]}
for fn, D in docs.items():
    assert not pending(D), f"{fn} holds PENDING"
    op = os.path.join(OUTD, fn); json.dump(D, open(op, "w"), indent=1, ensure_ascii=False)
    receipts["configs"][fn] = {"path": op, "sha256": sha(op), "runs": [r["tag"] for r in D["runs"]], "window": [D["window"]["first_anchor"], D["window"]["last_anchor"]]}
receipts["settings_identical_statement"] = "every differing leaf between an OVN_NEW config and OVN_OLD is in ALLOWED_NEW_VS_OLD (labels, arm/tag/role, target arm and sources, lineage); asserted"
receipts["allowed_new_vs_old"] = ALLOWED_NEW_VS_OLD; receipts["allowed_old_vs_certified"] = ALLOWED_OLD_VS_CERT
json.dump(receipts, open(DIFF, "w"), indent=1, ensure_ascii=False)
print("OVN_MAKE_CONFIGS VERDICT=PASS", {k: v["sha256"][:16] for k, v in receipts["configs"].items()}, "diff_receipt", sha(DIFF), flush=True)
