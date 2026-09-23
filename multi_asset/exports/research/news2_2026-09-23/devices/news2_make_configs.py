#!/usr/bin/env python3
"""news_make_configs.py — NEW_S run configurations derived by copy from the Stage 1 configs (ovn_make_configs.py), with the leaf-level
diff asserted before anything is written:
  RUN_CONFIG_NEWS2_s{42,2027}   = Stage 1 RUN_CONFIG_OVN_NEW_s{seed} with ONLY labels (config / status / created_utc / object / pending / ovn),
                                 per run arm / tag / role / targets.arm / targets.sources (this agent's adapter npz + receipt, shas pinned),
                                 new_lineage, and paths.pod_root (/dev/shm/news2_2026-09-23). Asserted against RUN_CONFIG_OVN_OLD:
                                 every differing leaf ∈ Stage 1's ALLOWED_NEW_VS_OLD ∪ {paths.pod_root} (the output root).
  RUN_CONFIG_NEWS2_s{seed}X     = the same substitutions on Stage 1 RUN_CONFIG_OVN_NEW_s{seed}X (describe-only extension, scaled main run only).
usage: python -B news_make_configs.py PATH,HOME,LC_CTYPE <out_dir> <adapter_receipt_s42> <adapter_receipt_s2027> <diff_receipt.json>
"""
import os, sys, json, time, hashlib, re

WL = set(sys.argv[1].split(",")); extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
OUTD, AR42, AR2027, DIFF = sys.argv[2:6]
S1 = "/workspace/old_vs_new_2026-09-23"; POD_ROOT = "/dev/shm/news2_2026-09-23"
STAGE1 = {"OLD": f"{S1}/RUN_CONFIG_OVN_OLD_2026-09-23.json", "NEW_s42": f"{S1}/RUN_CONFIG_OVN_NEW_s42_2026-09-23.json",
          "NEW_s2027": f"{S1}/RUN_CONFIG_OVN_NEW_s2027_2026-09-23.json", "NEW_s42X": f"{S1}/RUN_CONFIG_OVN_NEW_s42X_2026-09-23.json",
          "NEW_s2027X": f"{S1}/RUN_CONFIG_OVN_NEW_s2027X_2026-09-23.json", "OLD_HOLD": f"{S1}/RUN_CONFIG_OVN_OLD_HOLD_2026-09-23.json"}
PREREG = {"path": "docs/PREREG_new_servable_models_2026-09-23.md", "commit": "db0123df7", "amendment_1": {"path": "docs/AMENDMENT_1_new_servable_models_2026-09-23.md", "commit": "63ca0d0bb"}}
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


ALLOWED_NEWS_VS_OLD = [r"^config$", r"^status$", r"^created_utc$", r"^object$", r"^pending(\.|$)", r"^ovn(\.|$)", r"^objb_lineage(\.|$)", r"^new_lineage(\.|$)",
                       r"^runs\[\d+\]\.(arm|tag|role)$", r"^runs\[\d+\]\.targets\.arm$", r"^runs\[\d+\]\.targets\.sources(\[\d+\]\.(npz|npz_sha256|receipt|receipt_sha256))?$",
                       r"^paths\.pod_root$"]


def check(d, allowed, what):
    bad = [x["leaf"] for x in d if not any(re.search(p, x["leaf"]) for p in allowed)]
    assert not bad, f"{what}: leaves outside the allowed set (settings would differ): {bad[:10]}"


C = {k: json.load(open(p)) for k, p in STAGE1.items()}
AR = {}
for seed, p in (("42", AR42), ("2027", AR2027)):
    R = json.load(open(p)); assert R["arm"] == f"NEWS2_s{seed}" and R["roundtrip"]["scaled"]["bitwise_equal"] and R["roundtrip"]["lit"]["bitwise_equal"], "adapter receipt"
    R["_npz_path"] = f"{POD_ROOT}/targets/TARGETS_NEWS2_s{seed}.npz"; assert sha(R["_npz_path"]) == R["targets_npz_sha256"]
    AR[seed] = (p, R)
os.makedirs(OUTD, exist_ok=True)
rec = {"device": "news_make_configs.py", "self_sha256": sha(os.path.abspath(__file__)), "utc": NOW, "prereg": PREREG,
       "stage1_configs": {k: {"path": p, "sha256": sha(p)} for k, p in STAGE1.items()}, "pod_root": POD_ROOT, "configs": {}, "diffs": {}}


def news_cfg(base, seed, ext):
    N = json.loads(json.dumps(base)); p, R = AR[seed]; arm = f"NEWS2_s{seed}"; run_arm = f"NEWS2_s{seed}{'X' if ext else ''}"
    N["config"] = f"RUN_CONFIG_NEWS2_s{seed}{'X' if ext else ''}_2026-09-23"
    N["status"] = f"FROZEN before any NEW_S book number; arm {arm}; settings byte-identical to Stage 1 RUN_CONFIG_OVN_OLD{'X' if ext else ''} (only labels, targets and output root differ)"
    N["created_utc"] = NOW
    N["object"] = f"NEW_S arm {arm}: producer-code-replayed features, retrained King + F10 s{seed}, combo via combo_target (scaled_diagnostic = scaled reading, literal = lit reading), through ovn_adapter.py"
    N["pending"] = {"(a) targets": f"filled: TARGETS_{arm} (adapter round-trip bitwise PASS)", "(b) the controls": "Stage 1 OLD / OLD_HOLD runs (reused, path shas re-checked)"}
    N["ovn"] = dict(N["ovn"], role=f"NEW_S arm {arm}", news_prereg=PREREG, derived_by="news_make_configs.py")
    N["paths"]["pod_root"] = POD_ROOT
    N["new_lineage"] = {"arm": arm, "adapter_receipt": {"path": p, "sha256": sha(p)}, "new_target_receipt": R["adapter"]["new_receipt"], "sources": R["adapter"]["sources"]}
    for r in N["runs"]:
        old_arm = r["arm"]; r["arm"] = run_arm; r["tag"] = run_arm + "|" + r["tag"].split("|", 1)[1]
        r["role"] = re.sub(r"NEW arm NEW_s\d+", f"NEW_S arm {arm}", r["role"])
        r["targets"]["arm"] = arm
        r["targets"]["sources"] = [{"npz": R["_npz_path"], "npz_sha256": R["targets_npz_sha256"], "receipt": p, "receipt_sha256": sha(p)}]
    return N


docs = {}
for seed in ("42", "2027"):
    N = news_cfg(C[f"NEW_s{seed}"], seed, False); d = diff(C["OLD"], N); check(d, ALLOWED_NEWS_VS_OLD, f"NEWS2_s{seed} vs OVN_OLD"); rec["diffs"][f"NEWS2_s{seed}_vs_OVN_OLD"] = d
    d2 = diff(C[f"NEW_s{seed}"], N); check(d2, ALLOWED_NEWS_VS_OLD, f"NEWS2_s{seed} vs OVN_NEW_s{seed}"); rec["diffs"][f"NEWS2_s{seed}_vs_OVN_NEW_s{seed}"] = d2
    docs[f"RUN_CONFIG_NEWS2_s{seed}_2026-09-23.json"] = N
    NX = news_cfg(C[f"NEW_s{seed}X"], seed, True); d = diff(C[f"NEW_s{seed}X"], NX); check(d, ALLOWED_NEWS_VS_OLD, f"NEWS2_s{seed}X vs OVN_NEW_s{seed}X"); rec["diffs"][f"NEWS2_s{seed}X_vs_OVN_NEW_s{seed}X"] = d
    docs[f"RUN_CONFIG_NEWS2_s{seed}X_2026-09-23.json"] = NX
# OLD_HOLD control: Stage 1 config vs OLD, re-listed for the record (no new run)
rec["diffs"]["stage1_OVN_OLD_HOLD_vs_OVN_OLD_leaves"] = [x["leaf"] for x in diff(C["OLD"], C["OLD_HOLD"])]
for fn, D in docs.items():
    assert not [k for k, v in leaves(D).items() if v == "PENDING"], f"{fn} holds PENDING"
    op = os.path.join(OUTD, fn); json.dump(D, open(op, "w"), indent=1, ensure_ascii=False)
    rec["configs"][fn] = {"path": op, "sha256": sha(op), "runs": [r["tag"] for r in D["runs"]], "window": [D["window"]["first_anchor"], D["window"]["last_anchor"]]}
rec["settings_identical_statement"] = "every differing leaf between a NEWS config and Stage 1 OVN_OLD is labels / arm-tag-role / targets / lineage / output root; asserted"
rec["allowed"] = ALLOWED_NEWS_VS_OLD
json.dump(rec, open(DIFF, "w"), indent=1, ensure_ascii=False)
print("NEWS_MAKE_CONFIGS VERDICT=PASS", {k: v["sha256"][:16] for k, v in rec["configs"].items()}, "diff_receipt", sha(DIFF), flush=True)
