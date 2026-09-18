import hashlib, json, os, time, glob
R = "/workspace/fp3_live_2026-09"
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 24), b""): h.update(c)
    return h.hexdigest()
items = [("cache", "/workspace/data/dlnative_5m_wide829_f16_holefix2.npz"),
         ("hole_cells", "/workspace/review_scratch/holefix2_cells.npz"),
         ("mask_liveness", "/workspace/fp2_2026-09/masks/member_mask_tradable_AND_live_W24H_cachegrid.npz"),
         ("raw_patch", "/workspace/fp2_2026-09/raw_patch.npz"),
         ("dlw_raw_targets", R + "/dlw_v4raw/data/dlw_targets.npz"),
         ("dlw_clip_targets", R + "/dlw_hf3/data/dlw_targets.npz"),
         ("fea82", R + "/dlw_v4raw/data/dlw_fea82.npz"),
         ("fea89", R + "/f8_v4/data/f8_fea89.npz"),
         ("king_fea", R + "/data/wide_fea_v4.npy"),
         ("king_meta", R + "/data/wide_fea_v4_meta.npz"),
         ("king_slow_pred", R + "/shadow_bundle_L/slow_pred_pinned.npy"),
         ("king_booster", R + "/shadow_bundle_L/slow2026.txt"),
         ("legs", R + "/f8_v4/data/f10v2_legs.npz"),
         ("f10_live_s42", R + "/f8_v4/models/f10_live_s42.pt"),
         ("f10_live_s2027", R + "/f8_v4/models/f10_live_s2027.pt"),
         ("np_s42", R + "/np_export/f10_np_s42.npz"),
         ("np_s2027", R + "/np_export/f10_np_s2027.npz")]
arte = {}
for lab, p in items:
    e = os.path.exists(p)
    arte[lab] = {"path": p, "sha256": sha(p) if e else None, "bytes": os.path.getsize(p) if e else None}
want = {"pod_dlw_targets_raw_v2.py", "pod_fea_ext_clamp_v2.py", "pod_export_bundle_v4.py", "pod_legs_v4b.py",
        "pod_f10_train_monthly_v4.py", "pod_f10_refit_v4.py", "pod_f10_np_export_v4.py", "pod_dlw_features_ext.py", "pod_f8_build_ext.py"}
dev = {}
for p in glob.glob("/workspace/fp2_2026-09/devices_v4chain/pod_*.py") + ["/workspace/pod_dlw_features_ext.py", "/workspace/pod_f8_build_ext.py"]:
    b = os.path.basename(p)
    if b in want: dev[b] = sha(p)
mwf = {}
for f in sorted(glob.glob(R + "/f8_v4/mwf_v4b/RAW_s*/preds/*.npy"))[:6]: mwf[os.path.relpath(f, R)] = sha(f)
out = {"seal": "legal-member model artefacts, SEALED - trained and materialised, NOT judged. No book-level evaluation was run.",
       "why": "independent review round 14 section 5: keep the model artefacts sealed until the gates and the cash/replay closure are done.",
       "utc": time.strftime("%FT%TZ", time.gmtime()), "root": R,
       "member_rule": "MEMBER_LIVENESS = tradable W24H AND liveness; mask sha 9b59678b4529246c...",
       "training": {"mwf": "2 seeds x 4 disjoint month shards, 8/8 rc=0, 5 folds each, MWF_TRAIN_DONE, both merges MERGE_DONE",
                    "refit": "s42 best_va -6.861 alpha 0.092 / s2027 best_va -6.907 alpha 0.093, rule fix7, label cutoff 2025-12-16T20:00:00Z",
                    "king": "three-fold Spearman deltas +0.0027 / -0.0014 / +0.0002, inside the existing absolute tolerances .004/.006 = score-consistency guard passed; NOT a formal non-inferiority claim"},
       "artefacts": arte, "devices": dev, "mwf_preds_sample": mwf,
       "not_done": ["out-of-sample whole-book evaluation", "per-year / regime / 2x leverage return and maxDD", "export bundle for this model", "any swap recommendation"]}
json.dump(out, open(R + "/MODEL_SEAL.json", "w"), indent=1)
print("sealed", sum(1 for v in arte.values() if v["sha256"]), "artefacts,", len(dev), "devices")
for k, v in arte.items():
    if v["sha256"]: print("  %-18s %s %12s" % (k, v["sha256"][:16], v["bytes"]))
