"""AX14 (axis_0919): the diff proof x0918r (corrected 08-31) vs x0918, artifact by artifact. Pure reads; one JSON receipt.

  C1 cache: rows outside [LO, HI] uint16-identical (NaN payload included); inside: finite cells bitwise, NaN pattern, NaN-payload-only cells per channel
  C2 hole list: new == old minus exactly the cells of rows [LO, HI]; removed-cell count; runs / neighbourhoods dropped
  C3 tradability arrays, tradable mask: identical (their only input is the cache's log_cnt / ret5 values, unchanged)
  C4 liveness mask: every differing cell listed by anchor (count, first symbols); prediction = only anchors whose (A-24h, A] window touches [LO, HI]
  C5 rawbuild panel: every array key identical (=> the x0918 v2ext / v3splice panels are the x0918r panels)
  C6 DL targets RAW / CLIP, fea82, fea89, king features + meta, accounting meta: anchor sets (added / removed); per common anchor and key / column,
     cells that differ; the FULL list of changed anchors; and the attribution test:
        changed anchors ⊆ { anchors whose MEMBER set changed } ∪ { index-window anchors for fea89 families H (causal_z over 180 anchors by position)
        and J drank_* (anchor i-6) }  — anything outside is UNEXPLAINED (verdict FAIL).
env: AX_X (x0918 root) AX_R (x0918r root) AX_LO AX_HI AX_RECEIPT
"""
import os, json, time, hashlib, zipfile
import numpy as np
X, R = os.environ["AX_X"], os.environ["AX_R"]; LO, HI = int(os.environ["AX_LO"]), int(os.environ["AX_HI"]); RPT = os.environ["AX_RECEIPT"]
assert not os.path.exists(RPT)
U = lambda t: time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(int(t)))
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 24), b""): h.update(c)
    return h.hexdigest()
def neq(a, b):
    a = np.asarray(a); b = np.asarray(b)
    if a.dtype.kind == "f":
        na, nb = np.isnan(a), np.isnan(b); w = {2: np.uint16, 4: np.uint32, 8: np.uint64}[a.dtype.itemsize]
        return (na != nb) | (~na & ~nb & (a.view(w) != b.astype(a.dtype).view(w)))
    return a != b
out = {"device": "ax14_variant_diff.py", "self_sha256": sha(os.path.abspath(__file__)), "x0918_root": X, "x0918r_root": R, "replaced_rows": [LO, HI]}
T0 = time.time()
# ---------------- C1 cache (streamed)
CX = f"{X}/data/dlnative_5m_wide829_f16_holefix2_x0918.npz"; CR = f"{R}/data/dlnative_5m_wide829_f16_holefix2_x0918r.npz"
def opener(p):
    zf = zipfile.ZipFile(p); f = zf.open("data.npy"); v = np.lib.format.read_magic(f)
    sh, fo, dt = (np.lib.format.read_array_header_1_0(f) if v == (1, 0) else np.lib.format.read_array_header_2_0(f)); return f, sh, dt
fa, sa, da = opener(CX); fb, sb, db = opener(CR); assert sa == sb and da == db
rowb = int(np.prod(sa[1:])) * da.itemsize; N = sa[0]; done = 0; BLK = 20000
c1 = {"rows": int(N), "outside_cells": 0, "outside_uint16_diff": 0, "inside_cells": 0, "inside_finite_bit_diff": 0, "inside_nan_pattern_diff": 0, "inside_nan_payload_only_by_channel": {}}
chs = [str(c) for c in np.load(CX, allow_pickle=True)["ch"]]
while done < N:
    n = min(BLK, N - done); A = np.frombuffer(fa.read(n * rowb), dtype=da).reshape((n,) + tuple(sa[1:])); B = np.frombuffer(fb.read(n * rowb), dtype=db).reshape((n,) + tuple(sb[1:]))
    r = np.arange(done, done + n); ins = (r >= LO) & (r <= HI)
    if (~ins).any():
        c1["outside_cells"] += int(A[~ins].size); c1["outside_uint16_diff"] += int((A[~ins].view(np.uint16) != B[~ins].view(np.uint16)).sum())
    if ins.any():
        a, b = A[ins], B[ins]; na, nb = np.isnan(a), np.isnan(b); both = ~na & ~nb
        c1["inside_cells"] += int(a.size); c1["inside_nan_pattern_diff"] += int((na != nb).sum()); c1["inside_finite_bit_diff"] += int((a[both].view(np.uint16) != b[both].view(np.uint16)).sum())
        pay = na & nb & (a.view(np.uint16) != b.view(np.uint16))
        for c in range(pay.shape[2]):
            k = int(pay[:, :, c].sum())
            if k: c1["inside_nan_payload_only_by_channel"][chs[c]] = c1["inside_nan_payload_only_by_channel"].get(chs[c], 0) + k
    done += n
c1["PASS"] = c1["outside_uint16_diff"] == 0 and c1["inside_finite_bit_diff"] == 0 and c1["inside_nan_pattern_diff"] == 0
c1["x0918_sha256"] = sha(CX); c1["x0918r_sha256"] = sha(CR); out["C1_cache"] = c1; print("C1", json.dumps(c1), flush=True)
CTS = np.load(CX, allow_pickle=True)["ts"].astype(np.int64); SY = [str(s) for s in np.load(CX, allow_pickle=True)["symbols"]]
T_LO, T_HI = int(CTS[LO]), int(CTS[HI])
# ---------------- C2 holes
HX = np.load(f"{X}/inputs/holefix2_cells.npz", allow_pickle=True); HR = np.load(f"{R}/inputs/holefix2r_cells_x0918r.npz", allow_pickle=True)
kx = set(zip(HX["row"].tolist(), HX["col"].tolist())); kr = set(zip(HR["row"].tolist(), HR["col"].tolist()))
removed = kx - kr; added = kr - kx
out["C2_holes"] = {"n_x0918": len(kx), "n_x0918r": len(kr), "removed": len(removed), "added": len(added),
                   "removed_all_in_range": all(LO <= r <= HI for r, _ in removed), "range_cells_left_in_list": sum(1 for r, _ in kr if LO <= r <= HI),
                   "fill_runs_x0918": HX["fill_runs"].tolist(), "fill_runs_x0918r": HR["fill_runs"].tolist(), "neigh_rows_x0918r": HR["neigh_rows"].tolist()}
out["C2_holes"]["PASS"] = out["C2_holes"]["added"] == 0 and out["C2_holes"]["removed_all_in_range"]
print("C2", json.dumps(out["C2_holes"]), flush=True)
# ---------------- C3 tradability + tradable mask
TX = np.load(f"{X}/trd/tradability_v1.npz", allow_pickle=True); TR = np.load(f"{R}/trd/tradability_v1.npz", allow_pickle=True)
c3 = {"tradability_sha_x0918": sha(f"{X}/trd/tradability_v1.npz"), "tradability_sha_x0918r": sha(f"{R}/trd/tradability_v1.npz"),
      "keys_differing": [k for k in sorted(set(TX.files) | set(TR.files)) if k not in TX.files or k not in TR.files or not np.array_equal(TX[k], TR[k])]}
MTX = np.load(f"{X}/masks/member_mask_tradable_W24H_cachegrid.npz", allow_pickle=True); MTR = np.load(f"{R}/masks/member_mask_tradable_W24H_cachegrid.npz", allow_pickle=True)
c3["tradable_mask_sha_x0918"] = sha(f"{X}/masks/member_mask_tradable_W24H_cachegrid.npz"); c3["tradable_mask_sha_x0918r"] = sha(f"{R}/masks/member_mask_tradable_W24H_cachegrid.npz")
c3["tradable_mask_cells_diff"] = int((MTX["mask"] != MTR["mask"]).sum()) if MTX["mask"].shape == MTR["mask"].shape else "shape"
c3["PASS"] = not c3["keys_differing"] and c3["tradable_mask_cells_diff"] == 0
out["C3_tradability"] = c3; print("C3", json.dumps(c3), flush=True)
# ---------------- C4 liveness mask
LX = np.load(f"{X}/masks/member_mask_tradable_AND_live_W24H_cachegrid.npz", allow_pickle=True); LR = np.load(f"{R}/masks/member_mask_tradable_AND_live_W24H_cachegrid.npz", allow_pickle=True)
mts = LR["ts"].astype(np.int64); assert np.array_equal(mts, LX["ts"].astype(np.int64))
dm = LX["mask"] != LR["mask"]; ch_rows = np.nonzero(dm.any(1))[0]
touch = (mts > T_LO - 300) & (mts - 86400 < T_HI)        # (A-24h, A] intersects the replaced close times [T_LO, T_HI]
MASK_CHANGED_TS = set(int(t) for t in mts[ch_rows])
out["C4_liveness_mask"] = {"cells_diff": int(dm.sum()), "cells_false_to_true": int((~LX["mask"] & LR["mask"]).sum()), "cells_true_to_false": int((LX["mask"] & ~LR["mask"]).sum()),
                           "anchors_changed": [{"anchor": U(mts[i]), "cells": int(dm[i].sum()), "x0918_row_true": int(LX["mask"][i].sum()), "x0918r_row_true": int(LR["mask"][i].sum()),
                                                "symbols_first": [SY[j] for j in np.nonzero(dm[i])[0][:8]]} for i in ch_rows],
                           "changed_anchors_all_touch_range": bool(touch[ch_rows].all()), "anchors_touching_range": [U(t) for t in mts[touch]]}
out["C4_liveness_mask"]["PASS"] = out["C4_liveness_mask"]["changed_anchors_all_touch_range"] and out["C4_liveness_mask"]["cells_true_to_false"] == 0
print("C4", json.dumps(out["C4_liveness_mask"])[:1500], flush=True)
# ---------------- C5 rawbuild panel
PX = np.load(f"{X}/panels/wide_panel_4h_rawbuild_x0918.npz", allow_pickle=True); PR = np.load(f"{R}/panels/wide_panel_4h_rawbuild_x0918r.npz", allow_pickle=True)
c5 = {"keys": sorted(PX.files), "keys_missing": sorted(set(PX.files) ^ set(PR.files)), "shape_mismatch": [], "keys_differing": {}}
for k in sorted(set(PX.files) & set(PR.files)):
    x, y = PX[k], PR[k]
    if x.shape != y.shape: c5["shape_mismatch"].append(k); continue
    d = neq(x, y)
    if d.any(): c5["keys_differing"][k] = int(d.sum())
c5["PASS"] = not c5["keys_differing"] and not c5["shape_mismatch"] and not c5["keys_missing"]; out["C5_rawbuild_panel"] = c5; print("C5", json.dumps({k: v for k, v in c5.items() if k != "keys"}), flush=True)
# ---------------- C6 derived artifacts
def anchors_meta(p):
    Z = np.load(p, allow_pickle=True); return Z, Z["E_ts"].astype(np.int64)
def members_changed(AM, BM, ia, ib):
    return np.array([not np.array_equal(np.asarray(AM[i], int), np.asarray(BM[j], int)) for i, j in zip(ia, ib)])
def attribution(changed_ts, allowed_ts):
    return sorted(U(t) for t in set(changed_ts) - set(allowed_ts))
c6 = {}
def targets(name, px, pr):
    A, ea = anchors_meta(px); B, eb = anchors_meta(pr)
    com, ia, ib = np.intersect1d(ea, eb, return_indices=True)
    AM, BM = A["members"], B["members"]; mc = members_changed(AM, BM, ia, ib)
    r = {"n_x0918": int(len(ea)), "n_x0918r": int(len(eb)), "added": [U(t) for t in np.setdiff1d(eb, ea)], "removed": [U(t) for t in np.setdiff1d(ea, eb)],
         "members_changed_anchors": [U(t) for t in com[mc]], "per_key": {}}
    chg = set()
    for k in ("y4s", "y4old", "qvk", "btcv", "YR4s", "YRZ", "has_panel", "yrs"):
        d = neq(A[k][ia], B[k][ib]); dd = d.reshape(len(com), -1).any(1)
        r["per_key"][k] = {"cells_diff": int(d.sum()), "anchors_diff": [U(t) for t in com[dd]]}; chg |= set(int(t) for t in com[dd])
    chg |= set(int(t) for t in com[mc])
    r["changed_anchors"] = sorted(U(t) for t in chg); r["unexplained"] = attribution(chg, set(int(t) for t in com[mc]))
    r["PASS"] = not r["unexplained"] and not r["removed"]; c6[name] = r; print(name, json.dumps(r)[:1200], flush=True)
    return com, ia, ib, mc, ea, eb
comT, iaT, ibT, mcT, eaT, ebT = targets("targets_RAW", f"{X}/dlw_v4raw/data/dlw_targets.npz", f"{R}/dlw_v4raw/data/dlw_targets.npz")
targets("targets_CLIP", f"{X}/dlw_hf3/data/dlw_targets.npz", f"{R}/dlw_hf3/data/dlw_targets.npz")
MEMCHG_T = set(int(t) for t in comT[mcT])
def fea_long(name, px, pr, tx, tr, index_fams=()):
    A = np.load(px, allow_pickle=True); B = np.load(pr, allow_pickle=True); TA = np.load(tx, allow_pickle=True); TB = np.load(tr, allow_pickle=True)
    ea, eb = TA["E_ts"].astype(np.int64), TB["E_ts"].astype(np.int64); com, ia, ib = np.intersect1d(ea, eb, return_indices=True)
    names = [str(n) for n in A["names"]]; assert names == [str(n) for n in B["names"]]
    pa, pb = A["pair_a"].astype(np.int64), B["pair_a"].astype(np.int64); sa = np.searchsorted(pa, np.arange(len(ea) + 1)); sb = np.searchsorted(pb, np.arange(len(eb) + 1))
    XA, XB, PSA, PSB = A["X"], B["X"], A["pair_s"], B["pair_s"]
    col = np.zeros(len(names), np.int64); chg_anchor = {}; memdiff = []
    idx_cols = [q for q, n in enumerate(names) if n.split(":")[0] in index_fams]
    for k, (i, j) in enumerate(zip(ia, ib)):
        ra, rb = slice(sa[i], sa[i + 1]), slice(sb[j], sb[j + 1])
        if not np.array_equal(PSA[ra], PSB[rb]): memdiff.append(int(com[k])); chg_anchor[int(com[k])] = ["<members differ>"]; continue
        d = neq(XA[ra], XB[rb])
        if d.any():
            cd = d.any(0); col += d.sum(0); chg_anchor[int(com[k])] = [names[q] for q in np.nonzero(cd)[0]]
    only_index = [t for t, cols in chg_anchor.items() if cols != ["<members differ>"] and all(names.index(c) in idx_cols for c in cols)]
    allowed = MEMCHG_T | set(only_index)
    r = {"n_common": int(len(com)), "added": [U(t) for t in np.setdiff1d(eb, ea)], "anchors_members_differ": [U(t) for t in sorted(memdiff)],
         "changed_anchors": sorted(U(t) for t in chg_anchor), "n_changed_anchors": len(chg_anchor),
         "columns_with_diff": {names[q]: int(col[q]) for q in np.nonzero(col)[0]},
         "anchors_changed_only_in_index_window_columns": sorted(U(t) for t in only_index), "index_window_families": list(index_fams),
         "changed_anchor_first_columns": {U(t): cols[:10] for t, cols in sorted(chg_anchor.items())[:40]},
         "unexplained": attribution(set(chg_anchor), allowed)}
    r["PASS"] = not r["unexplained"]; c6[name] = r; print(name, json.dumps({k: v for k, v in r.items() if k != "changed_anchor_first_columns"})[:1500], flush=True)
fea_long("fea82", f"{X}/dlw_hf3/data/dlw_fea82.npz", f"{R}/dlw_hf3/data/dlw_fea82.npz", f"{X}/dlw_hf3/data/dlw_targets.npz", f"{R}/dlw_hf3/data/dlw_targets.npz")
fea_long("fea89", f"{X}/f8_v4/data/f8_fea89.npz", f"{R}/f8_v4/data/f8_fea89.npz", f"{X}/dlw_hf3/data/dlw_targets.npz", f"{R}/dlw_hf3/data/dlw_targets.npz", index_fams=("H", "J"))
# king (skipped, marked PENDING, while the x0918r king build has not produced its files)
KING_READY = os.path.exists(f"{R}/data/wide_fea_v4.npy") and os.path.exists(f"{R}/data/wide_fea_v4_meta.npz") and os.path.exists(f"{R}/meta/meta_newprod_v4_x0918r.npz")
if not KING_READY:
    c6["king"] = {"PENDING": True, "PASS": False}; c6["meta_newprod_v4"] = {"PENDING": True, "PASS": False}
if KING_READY:
  MA, ea = anchors_meta(f"{X}/data/wide_fea_v4_meta.npz")  ; MB, eb = anchors_meta(f"{R}/data/wide_fea_v4_meta.npz")
  com, ia, ib = np.intersect1d(ea, eb, return_indices=True); MAM, MBM = MA["members"], MB["members"]; mc = members_changed(MAM, MBM, ia, ib)
  FA = np.load(f"{X}/data/wide_fea_v4.npy", mmap_mode="r"); FB = np.load(f"{R}/data/wide_fea_v4.npy", mmap_mode="r"); names = [str(n) for n in MA["names"]]
  col = np.zeros(len(names), np.int64); chg = {}
  for k, (i, j) in enumerate(zip(ia, ib)):
      d = neq(np.asarray(FA[i]), np.asarray(FB[j]))
      if d.any() or mc[k]: col += d.sum(0); chg[int(com[k])] = [names[q] for q in np.nonzero(d.any(0))[0]]
  metad = {k: [U(t) for t in com[neq(MA[k][ia], MB[k][ib]).reshape(len(com), -1).any(1)]] for k in ("y4", "qvk")}
  MEMCHG_K = set(int(t) for t in com[mc])
  c6["king"] = {"n_x0918": int(len(ea)), "n_x0918r": int(len(eb)), "added": [U(t) for t in np.setdiff1d(eb, ea)], "removed": [U(t) for t in np.setdiff1d(ea, eb)],
                "members_changed_anchors": [U(t) for t in com[mc]], "changed_anchors": sorted(U(t) for t in chg), "columns_with_diff": {names[q]: int(col[q]) for q in np.nonzero(col)[0]},
                "meta_y4_qvk_changed_anchors": metad, "unexplained": attribution(set(chg), MEMCHG_K)}
  c6["king"]["PASS"] = not c6["king"]["unexplained"] and not c6["king"]["removed"] and not metad["y4"] and not metad["qvk"]
  print("king", json.dumps(c6["king"])[:1500], flush=True)
  # accounting meta
  A, ea = anchors_meta(f"{X}/meta/meta_newprod_v4_x0918.npz"); B, eb = anchors_meta(f"{R}/meta/meta_newprod_v4_x0918r.npz")
  com, ia, ib = np.intersect1d(ea, eb, return_indices=True); mc = members_changed(A["members"], B["members"], ia, ib)
  c6["meta_newprod_v4"] = {"n_x0918": int(len(ea)), "n_x0918r": int(len(eb)), "added": [U(t) for t in np.setdiff1d(eb, ea)], "removed": [U(t) for t in np.setdiff1d(ea, eb)],
                           "members_changed_anchors": [U(t) for t in com[mc]],
                           "y4_cells_diff": int(neq(A["y4"][ia], B["y4"][ib]).sum()), "qvk_cells_diff": int(neq(A["qvk"][ia], B["qvk"][ib]).sum())}
  if len(np.setdiff1d(eb, ea)):
      i_new = [int(np.searchsorted(eb, t)) for t in np.setdiff1d(eb, ea)]
      c6["meta_newprod_v4"]["added_anchor_detail"] = [{"anchor": U(eb[i]), "members": int(len(B["members"][i])), "member_y4_finite": int(np.isfinite(B["y4"][i][np.asarray(B["members"][i], int)]).sum())} for i in i_new]
  c6["meta_newprod_v4"]["PASS"] = c6["meta_newprod_v4"]["y4_cells_diff"] == 0 and c6["meta_newprod_v4"]["qvk_cells_diff"] == 0 and not c6["meta_newprod_v4"]["removed"]
  print("meta", json.dumps(c6["meta_newprod_v4"]), flush=True)
out["C6_derived"] = c6
# ---------------- axis of the variant + dead-contract check on the x0918r masks
for name, p in (("targets_RAW", f"{R}/dlw_v4raw/data/dlw_targets.npz"), ("targets_CLIP", f"{R}/dlw_hf3/data/dlw_targets.npz"), ("king_meta", f"{R}/data/wide_fea_v4_meta.npz"), ("meta_newprod_v4", f"{R}/meta/meta_newprod_v4_x0918r.npz")):
    if not os.path.exists(p): out.setdefault("axis_x0918r", {})[name] = "PENDING"; continue
    E = np.load(p, allow_pickle=True)["E_ts"].astype(np.int64); full = np.arange(E[0], E[-1] + 1, 14400)
    out.setdefault("axis_x0918r", {})[name] = {"n": int(len(E)), "first": U(E[0]), "last": U(E[-1]), "grid": int(len(full)), "missing": [U(t) for t in np.setdiff1d(full, E)]}
lt = TR["last_traded_ts"].astype(np.int64); dead = (mts[:, None] > lt[None, :] + 86400) & (lt[None, :] >= 0)
out["dead_contract_check_x0918r"] = {"liveness_mask_true_after_last_trade_plus_24h": int((LR["mask"] & dead).sum()), "tradable_mask_true_after_last_trade_plus_24h": int((MTR["mask"] & dead).sum())}
out["VERDICT"] = {"C1": c1["PASS"], "C2": out["C2_holes"]["PASS"], "C3": c3["PASS"], "C4": out["C4_liveness_mask"]["PASS"], "C5": c5["PASS"], **{k: v["PASS"] for k, v in c6.items()}}
out["wall_s"] = round(time.time() - T0, 1)
json.dump(out, open(RPT, "w"), indent=1, default=str)
print("AX14_DONE", json.dumps(out["VERDICT"]), json.dumps(out["axis_x0918r"]), json.dumps(out["dead_contract_check_x0918r"]), flush=True)
