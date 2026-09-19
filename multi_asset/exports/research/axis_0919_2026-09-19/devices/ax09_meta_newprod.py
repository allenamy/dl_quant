"""AX09 (axis_0919): accounting meta `meta_newprod_v4`-type on the extended axis — the meta part of build_dev_v4.py (L14-18) VERBATIM, nothing else
(no dev tree, no symlinks, no SLOW/FPRED files: those belong to stream O/R):
    meta = king meta (E_ts / members / qvk / names)  with  y4 <- RAW targets y4s (Π(1+r)−1 over rows E+1..E+48, raw patch applied), aligned by E_ts.
Caliber: docs CALIBER_PIN_v4_2026-09-11 §1 (记账元 = RAW y4s from dlw_v4raw); never the 5m cache ret5 (clipped at ±0.30).
Self-checks (report + hard asserts):
  S1 every king anchor has a targets row; symbols == cache symbols
  S2 vs the September REFERENCE meta (meta_newprod_v4.npz, unmasked v1 axis) on common anchors OUTSIDE hole neighbourhoods: y4 finite pattern equal,
     max|Δy4| <= 1e-6 (build_dev_v4 rule), qvk bitwise; members: masked build ⊆ reference, with every removal mask-False (reported per anchor)
  S3 y4 on the anchors AFTER the reference end: finite share among members (label completeness through the last anchor)
env: KING_META DLW_RAW_TARGETS CACHE HOLE_CELLS REF_META MEMBER_MASK OUT RECEIPT
"""
import numpy as np, os, json, time, hashlib, zipfile
e = os.environ.get
KING_META, TGP, CACHE, HOLE, REF, MASK, OUT, RPT = (e(k) for k in ("KING_META", "DLW_RAW_TARGETS", "CACHE", "HOLE_CELLS", "REF_META", "MEMBER_MASK", "OUT", "RECEIPT"))
for p in (OUT, RPT): assert not os.path.exists(p), f"refuse to overwrite {p}"
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 24), b""): h.update(c)
    return h.hexdigest()
U = lambda t: time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(int(t)))
t0 = time.time()
with zipfile.ZipFile(CACHE) as z:
    CTS = np.load(z.open("ts.npy")).astype(np.int64); csyms = np.load(z.open("symbols.npy"), allow_pickle=True)
# ---- VERBATIM build_dev_v4.py L14-18 (paths from env) ----
M4 = np.load(KING_META, allow_pickle=True); TG = np.load(TGP, allow_pickle=True)
E4 = M4["E_ts"].astype(np.int64); tt = TG["E_ts"].astype(np.int64); rt = {int(x): i for i, x in enumerate(tt)}; idx = np.array([rt[int(x)] for x in E4])
assert np.array_equal(TG["symbols"], csyms), "symbol order"
y4 = TG["y4s"][idx].astype(np.float32)
M4mem = M4["members"]
tmp = OUT[:-4] + ".tmp.npz"
np.savez_compressed(tmp, E_ts=E4, members=M4mem, y4=y4, qvk=M4["qvk"], names=M4["names"]); os.replace(tmp, OUT)
print("written", OUT, y4.shape, flush=True)
# ---- S2 vs reference ----
MR = np.load(REF, allow_pickle=True); ER = MR["E_ts"].astype(np.int64)
H = np.load(HOLE, allow_pickle=True); NEIGH = H["neigh_rows"]
com = np.intersect1d(E4, ER); i4 = np.searchsorted(E4, com); ir = np.searchsorted(ER, com); rows = np.searchsorted(CTS, com)
inn = np.zeros(len(com), bool)
for lo, hi in NEIGH: inn |= (rows >= lo) & (rows <= hi)
a = y4[i4][~inn]; b = MR["y4"][ir][~inn]; fa, fb = np.isfinite(a), np.isfinite(b)
MK = np.load(MASK, allow_pickle=True); mrow = {int(t): i for i, t in enumerate(MK["ts"].astype(np.int64))}; MM = np.asarray(MK["mask"])
assert [str(s) for s in MK["symbols"]] == [str(s) for s in csyms]
sub_ok = 0; sub_bad = []; n_removed = 0; n_removed_maskfalse = 0; n_added = []; MRM = MR["members"]   # materialise once
for k in np.nonzero(~inn)[0]:
    A = set(int(x) for x in M4mem[i4[k]]); B = set(int(x) for x in MRM[ir[k]])
    rem = B - A; add = A - B; mr = MM[mrow[int(com[k])]]
    n_removed += len(rem); n_removed_maskfalse += sum(1 for x in rem if not mr[x])
    if add: n_added.append((U(com[k]), len(add), len(B)))
    if not add and all(not mr[x] for x in rem): sub_ok += 1
    else: sub_bad.append((U(com[k]), len(add), len([x for x in rem if mr[x]])))
chk = {"n_common": int(len(com)), "n_outside_neigh": int((~inn).sum()), "finite_pattern_equal_outside": bool(np.array_equal(fa, fb)),
       "y4_maxabs_outside": float(np.abs(a[fa & fb] - b[fa & fb]).max()), "y4_bitwise_equal_outside": bool(np.array_equal(a.view(np.uint32)[fa & fb], b.view(np.uint32)[fa & fb])),
       "qvk_equal_outside": bool(np.array_equal(M4["qvk"][i4][~inn], MR["qvk"][ir][~inn], equal_nan=True)),
       "members_subset_with_mask_false_removals_anchors": int(sub_ok), "members_rule_violations": len(sub_bad), "members_rule_violation_first": sub_bad[:20],
       "members_removed_total": int(n_removed), "members_removed_mask_false": int(n_removed_maskfalse),
       "anchors_with_additions": len(n_added), "additions_first": n_added[:20],
       "note_additions": "an addition is legitimate only at reference anchors truncated at NTOP=400 (a masked name frees a slot): fp2_gate_lib members_subset_check rule"}
# ---- S3 label completeness after the reference end ----
after = E4 > ER.max()
fin_mem = [float(np.isfinite(y4[i][np.asarray(M4mem[i], int)]).mean()) for i in np.nonzero(after)[0]]
rep = {"device": "ax09_meta_newprod.py", "self_sha256": sha(os.path.abspath(__file__)), "env": {k: e(k) for k in ("KING_META", "DLW_RAW_TARGETS", "CACHE", "HOLE_CELLS", "REF_META", "MEMBER_MASK", "OUT", "RECEIPT")},
       "inputs_sha256": {"king_meta": sha(KING_META), "targets": sha(TGP), "ref_meta": sha(REF), "hole_cells": sha(HOLE), "member_mask": sha(MASK)},
       "out": OUT, "out_sha256": sha(OUT), "n_anchors": int(len(E4)), "first": U(E4[0]), "last": U(E4[-1]), "shape_y4": list(y4.shape),
       "S2_vs_reference": chk, "S3_after_reference": {"n_anchors": int(after.sum()), "first": U(E4[after][0]) if after.any() else None,
                                                      "last": U(E4[after][-1]) if after.any() else None,
                                                      "member_y4_finite_share_min": min(fin_mem) if fin_mem else None, "member_y4_finite_share_mean": float(np.mean(fin_mem)) if fin_mem else None},
       "wall_s": round(time.time() - t0, 1)}
rep["PASS"] = bool(chk["finite_pattern_equal_outside"] and chk["y4_maxabs_outside"] <= 1e-6 and chk["qvk_equal_outside"])
json.dump(rep, open(RPT, "w"), indent=1, default=str)
print("AX09_DONE", json.dumps({k: rep[k] for k in ("n_anchors", "first", "last", "S2_vs_reference", "S3_after_reference", "PASS")}, default=str), flush=True)
