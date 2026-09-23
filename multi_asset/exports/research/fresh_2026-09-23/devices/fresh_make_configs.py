#!/usr/bin/env python3
"""fresh_make_configs.py — FRESH run configurations derived BY COPY from the NEW_S configs (the control arm), with the
leaf-level diff asserted before anything is written (PREREG_fresh_models_newS_2026-09-23.md §2: "配置逐叶 diff 只允许标签 / 目标 / 输出根不同"):

  RUN_CONFIG_FRESH_s{42,2027}   = NEW_S RUN_CONFIG_NEWS_s{seed} with ONLY labels (config / status / created_utc / object / pending / ovn),
                                  per run arm / tag / role / targets.arm / targets.sources (this agent's adapter npz + receipt, shas pinned),
                                  new_lineage, and paths.pod_root (/dev/shm/fresh_2026-09-23).
  RUN_CONFIG_FRESH_s{seed}X     = the same substitutions on RUN_CONFIG_NEWS_s{seed}X (describe-only extension, scaled main run only).

Asserted twice: every differing leaf FRESH vs NEW_S, and FRESH vs Stage 1 RUN_CONFIG_OVN_OLD, is in the allowed set.
The allowed set is Stage 1's ALLOWED_NEW_VS_OLD as NEW_S used it, verbatim.
usage: python -B fresh_make_configs.py PATH,HOME,LC_CTYPE <out_dir> <adapter_receipt_s42> <adapter_receipt_s2027> <diff_receipt.json>
"""
import os, sys, json, time, hashlib, re

WL = set(sys.argv[1].split(",")); extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
OUTD, AR42, AR2027, DIFF = sys.argv[2:6]
S1 = "/workspace/old_vs_new_2026-09-23"; NS = "/dev/shm/news_2026-09-23/configs"; POD_ROOT = "/dev/shm/fresh_2026-09-23"
CONTROL = {"NEWS_s42": f"{NS}/RUN_CONFIG_NEWS_s42_2026-09-23.json", "NEWS_s2027": f"{NS}/RUN_CONFIG_NEWS_s2027_2026-09-23.json",
           "NEWS_s42X": f"{NS}/RUN_CONFIG_NEWS_s42X_2026-09-23.json", "NEWS_s2027X": f"{NS}/RUN_CONFIG_NEWS_s2027X_2026-09-23.json"}
STAGE1_OLD = f"{S1}/RUN_CONFIG_OVN_OLD_2026-09-23.json"
PREREG = {"path": "docs/PREREG_fresh_models_newS_2026-09-23.md", "commit": "b6e682e0a",
          "newS_prereg": {"path": "docs/PREREG_new_servable_models_2026-09-23.md", "commit": "db0123df7"},
          "newS_amendment_1": {"path": "docs/AMENDMENT_1_new_servable_models_2026-09-23.md", "commit": "63ca0d0bb"}}
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


# verbatim from news_make_configs.py (which took it from Stage 1's ovn_make_configs.py)
ALLOWED = [r"^config$", r"^status$", r"^created_utc$", r"^object$", r"^pending(\.|$)", r"^ovn(\.|$)", r"^objb_lineage(\.|$)", r"^new_lineage(\.|$)",
           r"^runs\[\d+\]\.(arm|tag|role)$", r"^runs\[\d+\]\.targets\.arm$", r"^runs\[\d+\]\.targets\.sources(\[\d+\]\.(npz|npz_sha256|receipt|receipt_sha256))?$",
           r"^paths\.pod_root$"]


def check(d, what):
    bad = [x["leaf"] for x in d if not any(re.search(p, x["leaf"]) for p in ALLOWED)]
    assert not bad, f"{what}: leaves outside the allowed set (settings would differ): {bad[:10]}"


C = {k: json.load(open(p)) for k, p in CONTROL.items()}
OLD = json.load(open(STAGE1_OLD))
AR = {}
for seed, p in (("42", AR42), ("2027", AR2027)):
    R = json.load(open(p)); assert R["arm"] == f"FRESH_s{seed}" and R["roundtrip"]["scaled"]["bitwise_equal"] and R["roundtrip"]["lit"]["bitwise_equal"], "adapter receipt"
    R["_npz_path"] = f"{POD_ROOT}/targets/TARGETS_FRESH_s{seed}.npz"; assert sha(R["_npz_path"]) == R["targets_npz_sha256"]
    AR[seed] = (p, R)
os.makedirs(OUTD, exist_ok=True)
rec = {"device": "fresh_make_configs.py", "self_sha256": sha(os.path.abspath(__file__)), "utc": NOW, "prereg": PREREG,
       "control_configs": {k: {"path": p, "sha256": sha(p)} for k, p in CONTROL.items()},
       "stage1_old_config": {"path": STAGE1_OLD, "sha256": sha(STAGE1_OLD)}, "pod_root": POD_ROOT, "configs": {}, "diffs": {}}


def fresh_cfg(base, seed, ext):
    N = json.loads(json.dumps(base)); p, R = AR[seed]; arm = f"FRESH_s{seed}"; run_arm = f"FRESH_s{seed}{'X' if ext else ''}"
    N["config"] = f"RUN_CONFIG_FRESH_s{seed}{'X' if ext else ''}_2026-09-23"
    N["status"] = f"FROZEN before any FRESH book number; arm {arm}; settings byte-identical to the NEW_S control config (only labels, targets and output root differ)"
    N["created_utc"] = NOW
    N["object"] = f"FRESH arm {arm}: NEW_S producer-replayed features, King calendar-month folds + F10 all-monthly full-gradient-window, embargo 6 anchors, seed {seed}; combo via combo_target (scaled_diagnostic = scaled reading, literal = lit reading), through ovn_adapter.py"
    N["pending"] = {"(a) targets": f"filled: TARGETS_{arm} (adapter round-trip bitwise PASS)", "(b) the control": "NEW_S same-seed runs (reused; config leaves diffed and asserted)"}
    N["ovn"] = dict(N["ovn"], role=f"FRESH arm {arm}", fresh_prereg=PREREG, derived_by="fresh_make_configs.py", control_arm=f"NEWS_s{seed}")
    N["paths"]["pod_root"] = POD_ROOT
    N["new_lineage"] = {"arm": arm, "adapter_receipt": {"path": p, "sha256": sha(p)}, "new_target_receipt": R["adapter"]["new_receipt"], "sources": R["adapter"]["sources"]}
    for r in N["runs"]:
        r["arm"] = run_arm; r["tag"] = run_arm + "|" + r["tag"].split("|", 1)[1]
        old_role = r["role"]
        r["role"] = re.sub(r"NEW_S arm NEWS_s\d+", f"FRESH arm {arm}", r["role"])
        # not every role names the arm (the cost-cell runs read "§3.4 cost cell fee_x1.25 on the main reading"):
        # require only that no role still names the control arm, and that any role that DID name it now names FRESH.
        assert "NEWS_s" not in r["role"], f"role still names the control arm: {r['role']}"
        if "NEWS_s" in old_role:
            assert f"FRESH arm {arm}" in r["role"], f"role relabel did not take: {old_role} -> {r['role']}"
        r["targets"]["arm"] = arm
        r["targets"]["sources"] = [{"npz": R["_npz_path"], "npz_sha256": R["targets_npz_sha256"], "receipt": p, "receipt_sha256": sha(p)}]
    return N


docs = {}
for seed in ("42", "2027"):
    N = fresh_cfg(C[f"NEWS_s{seed}"], seed, False)
    d = diff(C[f"NEWS_s{seed}"], N); check(d, f"FRESH_s{seed} vs NEWS_s{seed}"); rec["diffs"][f"FRESH_s{seed}_vs_NEWS_s{seed}"] = d
    d2 = diff(OLD, N); check(d2, f"FRESH_s{seed} vs OVN_OLD"); rec["diffs"][f"FRESH_s{seed}_vs_OVN_OLD"] = d2
    docs[f"RUN_CONFIG_FRESH_s{seed}_2026-09-23.json"] = N
    NX = fresh_cfg(C[f"NEWS_s{seed}X"], seed, True)
    dx = diff(C[f"NEWS_s{seed}X"], NX); check(dx, f"FRESH_s{seed}X vs NEWS_s{seed}X"); rec["diffs"][f"FRESH_s{seed}X_vs_NEWS_s{seed}X"] = dx
    docs[f"RUN_CONFIG_FRESH_s{seed}X_2026-09-23.json"] = NX
for fn, D in docs.items():
    assert not [k for k, v in leaves(D).items() if v == "PENDING"], f"{fn} holds PENDING"
    op = os.path.join(OUTD, fn); json.dump(D, open(op, "w"), indent=1, ensure_ascii=False)
    rec["configs"][fn] = {"path": op, "sha256": sha(op), "runs": [r["tag"] for r in D["runs"]], "window": [D["window"]["first_anchor"], D["window"]["last_anchor"]]}
rec["settings_identical_statement"] = "every differing leaf between a FRESH config and its NEW_S control (and Stage 1 OVN_OLD) is labels / arm-tag-role / targets / lineage / output root; asserted"
rec["allowed"] = ALLOWED
json.dump(rec, open(DIFF, "w"), indent=1, ensure_ascii=False)
print("FRESH_MAKE_CONFIGS VERDICT=PASS", {k: v["sha256"][:16] for k, v in rec["configs"].items()}, "diff_receipt", sha(DIFF), flush=True)
