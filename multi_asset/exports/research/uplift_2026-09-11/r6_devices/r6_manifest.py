"""R6 final manifest: every original and every extension side by side, both sha256, both axis extents."""
import numpy as np, hashlib, json, os, time
def sha(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for c in iter(lambda: f.read(1<<24), b""): h.update(c)
    return h.hexdigest()
def U(t): return time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(int(t)))
def axis(p):
    try:
        if p.endswith(".npy"):
            a = np.load(p, mmap_mode="r"); return {"shape": list(a.shape)}
        Z = np.load(p, allow_pickle=True)
        for k in ("ts", "E_ts"):
            if k in Z.files:
                t = Z[k].astype(np.int64); return {"axis_key": k, "n": int(len(t)), "start": U(t[0]), "end": U(t[-1])}
        return {"keys": sorted(Z.files)[:8]}
    except Exception as e:
        return {"err": str(e)[:80]}
O = "/workspace/uplift_2026-09-11/r6/out"
PAIRS = [
 ("5m cache",            "/workspace/data/dlnative_5m_wide829_f16_holefix2.npz", "/workspace/data/dlnative_5m_wide829_f16_holefix2_x0910.npz"),
 ("4h panel v2ext",      "/workspace/data/wide_panel_4h_v2ext.npz",              f"{O}/wide_panel_4h_v2ext_x0910.npz"),
 ("4h panel v3splice",   "/workspace/data/wide_panel_4h_v3splice.npz",           f"{O}/wide_panel_4h_v3splice_x0910.npz"),
 ("king features",       "/workspace/data/wide_fea_v4.npy",                      f"{O}/wide_fea_v4_x0910.npy"),
 ("king meta",           "/workspace/data/wide_fea_v4_meta.npz",                 f"{O}/wide_fea_v4_meta_x0910.npz"),
 ("DL targets (RAW)",    "/workspace/dlw_v4raw/data/dlw_targets.npz",            f"{O}/dlw_targets_x0910.npz"),
 ("raw patch (E-0908-B)","/workspace/review_scratch/raw_patch.npz",              f"{O}/raw_patch_x0910.npz"),
 ("king preds",          "/workspace/shadow_bundle_v4/slow_pred_pinned.npy",     f"{O}/SLOW_v4_x0910.npy"),
 ("legs (v4b policy)",   "/workspace/f8_v4/data/f10v2_legs.npz",                 f"{O}/f10v2_legs_x0910.npz"),
 ("legs (WL repair5)",   "/workspace/f8_v4/data/f10v2_legs.npz",                 f"{O}/f10v2_legs_x0910_repair5.npz"),
 ("device meta",         "/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz", f"{O}/meta_newprod_v4_x0910.npz"),
 ("dlw fea82",           "/workspace/dlw_v4raw/data/dlw_fea82.npz",              f"{O}/dlw_hf3_x0910/data/dlw_fea82.npz"),
 ("f8 fea89",            "/workspace/f8_v4/data/f8_fea89.npz",                   f"{O}/f8_v4_x0910/data/f8_fea89.npz"),
]
rows = []
for nm, a, b in PAIRS:
    r = {"artifact": nm, "original": a, "extension": b,
         "original_sha256": sha(a) if os.path.exists(a) else None,
         "extension_sha256": sha(b) if os.path.exists(b) else None,
         "original_axis": axis(a) if os.path.exists(a) else "MISSING",
         "extension_axis": axis(b) if os.path.exists(b) else "NOT BUILT"}
    rows.append(r)
    o = r["original_axis"]; e = r["extension_axis"]
    print(f"{nm:22s} orig {str(o.get('n') if isinstance(o,dict) else o):>6} {str(o.get('end','') if isinstance(o,dict) else ''):>18}  ->  ext {str(e.get('n') if isinstance(e,dict) else e):>6} {str(e.get('end','') if isinstance(e,dict) else ''):>18}", flush=True)
    print(f"{'':22s} sha {str(r['original_sha256'])[:16]} -> {str(r['extension_sha256'])[:16]}", flush=True)
json.dump({"pairs": rows, "built_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
          open("/workspace/uplift_2026-09-11/r6/MANIFEST_r6_extension.json","w"), indent=1)
print("R6_MANIFEST_DONE", flush=True)
