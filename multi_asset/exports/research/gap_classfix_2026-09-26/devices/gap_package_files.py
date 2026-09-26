#!/usr/bin/env python3
"""gap_package_files.py — FILES-ONLY release package for the gap class fix (schema nc_files_contract_v1, installed by the unchanged
nc_2026-09-23/devices/nc_install_files.py {preflight|apply|rollback}). Built from a make_tree.py tree (PATCH_RECEIPT gap_classfix=True).
No state, no model, no archive move. Files: fea171/combo_stage.py (changed), fea171/prev_state.py, fea171/members_rule.py,
fea171/tests_prev_state.py (new). `unchanged` pins every production file the patched stage imports or reads besides state, so a drift
between packaging and install refuses.
usage: ~/wide_shadow/venv/bin/python gap_package_files.py <tree> <out dir> --label L"""
import argparse, hashlib, json, os, time

HOME = os.path.expanduser("~")
PINNED_UNCHANGED = ["wide_shadow/shadow_bundle/config.json", "wide_shadow/shadow_bundle/MANIFEST.json", "wide_shadow/shadow_bundle/slow2026.txt",
                    "wide_shadow/shadow_bundle/crypto_axis.json", "wide_shadow/fea171/f10_live_s42_np.npz", "wide_shadow/shadow_loop_v3.py",
                    "wide_shadow/fea171/nc_contract.py", "wide_shadow/fea171/tradability.py", "wide_shadow/fea171/feature_cache_identity.py",
                    "wide_shadow/fea171/durable_io.py", "wide_shadow/fea171/dlw_features.py", "wide_shadow/fea171/f8_higher_order_features.py",
                    "wide_shadow/fea171/beta_overlay_producer.py", "wide_shadow/fea171/combo_live_daemon.sh"]
BASE_COMBO = "12a76de89831fb42d05ec722f2e2506d6b288b4b9f5b86be04bc390c789a62a9"


def sha_b(b): return hashlib.sha256(b).hexdigest()
def sha(p):
    with open(p, "rb") as f: return sha_b(f.read())


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("tree"); ap.add_argument("out"); ap.add_argument("--label", required=True)
    ap.add_argument("--home", default=HOME); a = ap.parse_args()
    assert not os.path.exists(a.out), f"refusing to overwrite {a.out}"
    tree = os.path.abspath(a.tree); rec_t = json.load(open(f"{tree}/PATCH_RECEIPT.json"))
    assert rec_t.get("gap_classfix") and rec_t["base"]["fea171/combo_stage.py"] == BASE_COMBO, "not a gap-class-fix tree on 12a76de8"
    files, unchanged = [], {}
    for rel in sorted(rec_t["files"]):
        raw = open(f"{tree}/{rel}", "rb").read(); assert sha_b(raw) == rec_t["files"][rel], f"tree file differs from its receipt: {rel}"
        dest = f"wide_shadow/{rel}"; cur = f"{a.home}/{dest}"; base = sha(cur) if os.path.exists(cur) else None
        if base == sha_b(raw):
            unchanged[dest] = base; continue
        p = f"{a.out}/files/{dest}"; os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as fh: fh.write(raw)
        os.chmod(p, 0o644)
        files.append({"dest": dest, "candidate_sha256": sha_b(raw), "baseline_sha256": base})
    assert any(f["dest"] == "wide_shadow/fea171/combo_stage.py" and f["baseline_sha256"] == BASE_COMBO for f in files), "production combo_stage is not at 12a76de8"
    for u in PINNED_UNCHANGED:
        unchanged[u] = sha(f"{a.home}/{u}")
    C = {"schema": "nc_files_contract_v1", "label": a.label, "built_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
         "device_sha256": sha(os.path.abspath(__file__)), "home": a.home, "tree": tree, "tree_receipt_sha256": sha(f"{tree}/PATCH_RECEIPT.json"),
         "files": files, "archive_moves": [], "unchanged": dict(sorted(unchanged.items())),
         "services": {"stop": ["com.hsy.shadowloop", "com.hsy.combolive", "com.hsy.combosnap", "com.hsy.comboparity"], "not_loaded": ["com.hsy.sidecar"]},
         "forbidden_dest_prefixes": ["wide_shadow/state/"],
         "release_basis": {"statement": "code-only producer release: gap class fix (combo_stage previous state = most recent valid state before A with a "
                                        "named source and a declared bound; member history of anchors the producer never ran recomputed with the producer "
                                        "rule). No model, state or book-configuration change; with no gap the outputs are byte-identical (receipt C0). "
                                        "Acceptance: multi_asset/exports/research/gap_classfix_2026-09-26/ACCEPTANCE_gap_classfix_2026-09-26.md."}}
    os.makedirs(a.out, exist_ok=True)
    with open(f"{a.out}/INSTALL_CONTRACT.json", "w") as fh:
        json.dump(C, fh, indent=1)
    print("GAP_PACKAGE_FILES_OK", json.dumps({"files": [(it["dest"], it["candidate_sha256"][:12], (it["baseline_sha256"] or "NEW")[:12]) for it in files],
                                              "unchanged": len(unchanged), "contract_sha256": sha(f"{a.out}/INSTALL_CONTRACT.json")}), flush=True)


if __name__ == "__main__":
    main()
