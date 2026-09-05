"""make_pinned_on_hist.py — ADAPTER (path/format only): the in-service pinned king /workspace/shadow_bundle_v3/slow_pred_pinned.npy is laid out
on the v2ext meta anchor grid (/workspace/data/wide_fea_v2ext_meta.npz E_ts, 10,176 anchors, 2022-01-03..2026-08-31); the recheck device
requires SLOW_NPY to have the shape of the canonical king in its layout (rebuilt hist meta, 12,985 anchors expected). This re-indexes the
pinned predictions onto the rebuilt hist meta anchors by timestamp (NaN where the pinned grid has no row); the symbol axis is asserted
identical (829, same order). Receipt: every finite output cell equals the pinned cell at the same (ts, symbol) — verified after writing.
Output: data/slow_pred_pinned_on_hist.npy. No value is altered."""
import os, json, time, hashlib
import numpy as np
ROOT = os.environ.get("JR_ROOT", "/workspace/review_scratch/jpline_rebuild")   # JR_ROOT only for the dry-test harness
SRC = "/workspace/shadow_bundle_v3/slow_pred_pinned.npy"; SRC_META = "/workspace/data/wide_fea_v2ext_meta.npz"; SRC_PANEL = "/workspace/data/wide_panel_4h_v2ext.npz"
DST_META = f"{ROOT}/data/wide_fea_hist_meta_rebuilt.npz"; DST_PANEL = f"{ROOT}/data/wide_panel_4h_hist_v2_rebuilt.npz"; OUT = f"{ROOT}/data/slow_pred_pinned_on_hist.npy"
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""): h.update(ch)
    return h.hexdigest()
P = np.load(SRC); mS = np.load(SRC_META, allow_pickle=True); mD = np.load(DST_META, allow_pickle=True)
tS = mS["E_ts"].astype(np.int64); tD = mD["E_ts"].astype(np.int64)
assert P.shape == (len(tS), 829), (P.shape, len(tS))
symS = [str(s) for s in np.load(SRC_PANEL, allow_pickle=True)["symbols"]]; symD = [str(s) for s in np.load(DST_PANEL, allow_pickle=True)["symbols"]]
assert symS == symD and len(symS) == 829, "symbol axes differ"
rowS = {int(t): i for i, t in enumerate(tS)}
Q = np.full((len(tD), 829), np.nan, np.float32); n_map = 0
for i, t in enumerate(tD):
    k = rowS.get(int(t))
    if k is not None: Q[i] = P[k]; n_map += 1
np.save(OUT, Q)
# receipt
Q2 = np.load(OUT); ok = 0; tot = 0
for i, t in enumerate(tD):
    k = rowS.get(int(t))
    if k is None: assert not np.isfinite(Q2[i]).any(); continue
    tot += 1; ok += int(np.array_equal(Q2[i], P[k], equal_nan=True))
yrsD = np.array([time.gmtime(int(t)).tm_year for t in tD])
rep = {"src": SRC, "src_sha256": sha(SRC), "src_shape": list(P.shape), "src_first": time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(tS[0]))), "src_last": time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(tS[-1]))),
       "dst_meta": DST_META, "dst_shape": list(Q.shape), "n_dst_anchors_mapped": n_map, "n_dst_anchors_unmapped": int(len(tD) - n_map),
       "rows_bitwise_equal_to_src": f"{ok}/{tot}", "finite_frac_by_year": {str(y): float(np.isfinite(Q2[yrsD == y]).mean()) for y in sorted(set(yrsD.tolist()))},
       "out": OUT, "out_sha256": sha(OUT), "self_sha256": sha(os.path.abspath(__file__))}
json.dump(rep, open(f"{ROOT}/results/pinned_on_hist_receipt.json", "w"), indent=1)
print("PINNED_ON_HIST", json.dumps(rep), flush=True)
assert ok == tot and n_map > 0
