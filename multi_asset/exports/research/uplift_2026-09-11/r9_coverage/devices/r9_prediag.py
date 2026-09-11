"""R9 — diagnose the GATE X-PRE failure: WHERE does the r6 extended feature matrix differ from the
incumbent on the shared prefix rows? Per column, per anchor, with named columns. READ-ONLY.
ENV whitelist = EMPTY SET."""
import os, json, time, hashlib, numpy as np
_KNOBS = ["F10_DLW","F10_OUT","MWF_OUT","SEED","ARM","V2","MWF_ROOT"]
assert {k: os.environ.get(k) for k in _KNOBS if os.environ.get(k) is not None} == {}
def iso(t): return time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(int(t)))
INC82 = "/workspace/dlw_v4raw/data/dlw_fea82.npz"
EXT82 = "/workspace/uplift_2026-09-11/r6/out/dlw_hf3_x0910/data/dlw_fea82.npz"
INC89 = "/workspace/f8_v4/data/f8_fea89.npz"
EXT89 = "/workspace/uplift_2026-09-11/r6/out/f8_v4_x0910/data/f8_fea89.npz"
TGI = "/workspace/dlw_v4raw/data/dlw_targets.npz"
E = np.load(TGI, allow_pickle=True)["E_ts"].astype(np.int64); nA = len(E)
A = np.load(INC82, allow_pickle=True); B = np.load(EXT82, allow_pickle=True)
pa = A["pair_a"].astype(np.int64); ST = np.searchsorted(pa, np.arange(nA + 1)); n_i = len(pa)
nm82 = json.loads(str(np.load(INC82, allow_pickle=True)["meta_json"]))["names"]
mjB = json.loads(str(B["meta_json"]))
OUT = {"ext82_meta": {k: mjB.get(k) for k in ("n_pairs","n_anchors","cache_sha256","panel_sha256","targets_sha256","self_sha256","anchors_without_panel_row")},
       "inc82_meta": {k: json.loads(str(A["meta_json"])).get(k) for k in ("n_pairs","n_anchors","cache_sha256","panel_sha256","targets_sha256","self_sha256","anchors_without_panel_row")}}
def diag(Xi, Xe, names, tag):
    d = np.abs(Xi - Xe)
    fi, fe = np.isfinite(Xi), np.isfinite(Xe)
    both = fi & fe
    dif_cell = np.zeros(Xi.shape, bool)
    dif_cell[both] = Xi[both] != Xe[both]
    dif_cell |= (fi != fe)
    percol = []
    for c in range(Xi.shape[1]):
        nd = int(dif_cell[:, c].sum())
        if nd:
            dd = d[:, c][both[:, c] & dif_cell[:, c]]
            percol.append({"col": c, "name": names[c] if c < len(names) else f"c{c}",
                           "n_diff_cells": nd, "maxabs": float(dd.max()) if dd.size else None,
                           "n_nanpattern_diff": int((fi[:, c] != fe[:, c]).sum())})
    rows = np.nonzero(dif_cell.any(1))[0]
    anch = np.unique(np.searchsorted(ST, rows, side="right") - 1) if rows.size else np.array([], int)
    return {"tag": tag, "n_diff_cells": int(dif_cell.sum()), "n_diff_rows": int(len(rows)),
            "maxabs_overall": float(d[both].max()) if both.any() else None,
            "per_column": percol,
            "n_anchors_touched": int(len(anch)),
            "anchors_touched_first10": [iso(E[i]) for i in anch[:10]],
            "anchors_touched_last10": [iso(E[i]) for i in anch[-10:]],
            "anchor_idx_min": int(anch.min()) if anch.size else None,
            "anchor_idx_max": int(anch.max()) if anch.size else None}
OUT["fea82"] = diag(A["X"], B["X"][:n_i], nm82, "fea82")
del A, B
A9 = np.load(INC89, allow_pickle=True); B9 = np.load(EXT89, allow_pickle=True)
try: nm89 = json.loads(str(A9["meta_json"]))["names"]
except Exception: nm89 = []
OUT["fea89"] = diag(A9["X"], B9["X"][:n_i], nm89, "fea89")
OUT["fea89_meta_ext"] = {k: json.loads(str(B9["meta_json"])).get(k) for k in ("n_pairs","n_anchors","self_sha256")} if "meta_json" in B9.files else None
print(json.dumps(OUT, indent=1))
