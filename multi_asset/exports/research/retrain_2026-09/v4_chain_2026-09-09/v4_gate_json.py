"""Writes the F10_GATE_JSON receipts the v4 trainer asserts against (keys must be a subset of the trainer's rep at gate time: targets/fea82/fea89 sha256)."""
import hashlib, json, os, time
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""): h.update(ch)
    return h.hexdigest()
f82 = sha("/workspace/dlw_v4raw/data/dlw_fea82.npz"); assert f82 == sha("/workspace/dlw_hf3/data/dlw_fea82.npz"), "fea82 copy differs"
f89 = sha("/workspace/f8_v4/data/f8_fea89.npz")
os.makedirs("/workspace/f8_v4/gates", exist_ok=True)
for arm, dlw in (("RAW", "/workspace/dlw_v4raw"), ("CLIP", "/workspace/dlw_hf3")):
    g = {"targets_sha256": sha(f"{dlw}/data/dlw_targets.npz"), "fea82_sha256": f82, "fea89_sha256": f89}
    json.dump(g, open(f"/workspace/f8_v4/gates/F10_GATE_{arm}.json", "w"), indent=1); print(arm, json.dumps(g))
prov = {"cache_holefix2_sha256": sha("/workspace/data/dlnative_5m_wide829_f16_holefix2.npz"), "raw_patch_sha256": sha("/workspace/review_scratch/raw_patch.npz"),
        "panel_v3splice_sha256": sha("/workspace/data/wide_panel_4h_v3splice.npz"), "panel_v2ext_sha256": sha("/workspace/data/wide_panel_4h_v2ext.npz"),
        "king_fea_v4_sha256": sha("/workspace/data/wide_fea_v4.npy"), "king_meta_v4_sha256": sha("/workspace/data/wide_fea_v4_meta.npz"),
        "scripts": {s: sha(f"/workspace/review_scratch/{s}") for s in ("pod_dlw_targets_raw.py", "pod_fea_ext_clamp.py", "chain_v4_data.sh", "pod_f10_train_monthly_v4.py", "pod_export_bundle_v4.py", "pod_f10_refit_v4.py", "pod_legs_v4.py")},
        "chain_log_sha256": sha("/workspace/review_scratch/chain_v4_data.log"), "built_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
json.dump(prov, open("/workspace/f8_v4/gates/PROVENANCE_v4_chain.json", "w"), indent=1); print(json.dumps(prov, indent=1))
