"""Single-fold diagnostics for the v4 DL spectrum collapse (V3′ k0 0.004 vs HF2 0.018). Builds:
 /workspace/diag_legs/data/{f8_fea89.npz -> f8_v4 fea89 (symlink), f10v2_legs.npz = f8_ext legs aligned to the v4 axis (10212; the 6 new anchors get NaN Z/WL=1/3)}
 and a DIAG copy of the v4 trainer whose whitelist accepts (dlw_hf3|dlw_ext) x (f8_v4|f8_ext|diag_legs) and skips the gate JSON when F10_GATE_JSON=SKIP (diagnostic device, not the gate device)."""
import numpy as np, os, json
os.makedirs("/workspace/diag_legs/data", exist_ok=True); os.makedirs("/workspace/diag_legs/models", exist_ok=True)
if not os.path.exists("/workspace/diag_legs/data/f8_fea89.npz"): os.symlink("/workspace/f8_v4/data/f8_fea89.npz", "/workspace/diag_legs/data/f8_fea89.npz")
L = np.load("/workspace/f8_ext/data/f10v2_legs.npz", allow_pickle=True); E = L["E_ts"].astype(np.int64); LZ24 = L["Z24"]; LZFD = L["ZFD"]; LWL = L["WL"]   # materialise once (NpzFile[key] in a loop re-reads)
E4 = np.load("/workspace/dlw_hf3/data/dlw_targets.npz", allow_pickle=True)["E_ts"].astype(np.int64); r = {int(t): i for i, t in enumerate(E)}
Z24 = np.full((len(E4), 829), np.nan, np.float32); ZFD = np.full((len(E4), 829), np.nan, np.float32); WL = np.full((len(E4), 3), 1/3, np.float32); n = 0
for k, t in enumerate(E4):
    i = r.get(int(t))
    if i is not None: Z24[k] = LZ24[i]; ZFD[k] = LZFD[i]; WL[k] = LWL[i]; n += 1
np.savez("/workspace/diag_legs/data/f10v2_legs.npz", Z24=Z24, ZFD=ZFD, WL=WL, E_ts=E4, meta_json=json.dumps({"note": "DIAG: f8_ext legs (old rows verbatim + v3 pinned new rows) aligned to the v4 axis", "rows_aligned": n}))
print("aligned legs rows", n, "/", len(E4))
s = open("/workspace/review_scratch/pod_f10_train_monthly_v4.py").read()
old = 'and DLW in ("/workspace/dlw_v4raw", "/workspace/dlw_hf3") and OUT == "/workspace/f8_v4", "env whitelist (V2MAIN recipe on the v4 chain) violated"'
new = 'and DLW in ("/workspace/dlw_v4raw", "/workspace/dlw_hf3", "/workspace/dlw_ext") and OUT in ("/workspace/f8_v4", "/workspace/f8_ext", "/workspace/diag_legs"), "env whitelist (DIAG single-fold device) violated"'
assert old in s; s = s.replace(old, new)
old2 = '_GATE_V4 = json.load(open(os.environ["F10_GATE_JSON"]))'
new2 = '_GATE_V4 = {} if os.environ["F10_GATE_JSON"] == "SKIP" else json.load(open(os.environ["F10_GATE_JSON"]))   # DIAG: gate skipped on request'
assert old2 in s; s = s.replace(old2, new2); open("/workspace/review_scratch/pod_f10_train_monthly_diag.py", "w").write(s); print("diag trainer written")
