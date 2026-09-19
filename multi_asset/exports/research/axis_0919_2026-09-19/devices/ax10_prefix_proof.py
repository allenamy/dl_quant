"""AX10 (axis_0919): append-only / prefix-identity proof for the DERIVED artifacts (targets, fea82, fea89, king features + meta, masks, tradability,
accounting meta) against the most recent same-builder reference builds. Pure reads; one JSON receipt.

For each pair (mine, reference): the common anchors (by E_ts / ts) are compared cell by cell, NaN-aware and BITWISE (uint view), key by key. Every
differing cell is counted and attributed to its anchor; anchors are classified so that an expected difference is NAMED, not waved through:
  - 'ref_no_panel_row'  : the reference build had no panel row at that anchor (its panel ended 20 h before its axis end) and mine has one ⇒ panel-derived
                          columns (YR4s/YRZ/has_panel, fund_ema/fund_now features) legitimately differ; all other columns must still be equal
  - 'members_differ'    : member sets differ (long-format feature rows cannot be aligned; counted, never compared)
  - otherwise           : any difference is UNEXPLAINED (the verdict fails)
env: AX_SPEC (json list of comparisons, see ax10 launch), AX_RECEIPT
"""
import os, json, time, hashlib, sys
import numpy as np
SPEC = json.loads(os.environ["AX_SPEC"]); RPT = os.environ["AX_RECEIPT"]; assert not os.path.exists(RPT)
U = lambda t: time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(int(t)))
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 24), b""): h.update(c)
    return h.hexdigest()
def neq(a, b):
    """cell-wise 'not identical' (NaN == NaN; bit patterns for floats)."""
    a = np.asarray(a); b = np.asarray(b)
    if a.dtype.kind == "f":
        na, nb = np.isnan(a), np.isnan(b)
        w = {2: np.uint16, 4: np.uint32, 8: np.uint64}[a.dtype.itemsize]
        return (na != nb) | (~na & ~nb & (a.view(w) != b.astype(a.dtype).view(w)))
    return a != b
def maxabs(a, b):
    a = np.asarray(a, np.float64); b = np.asarray(b, np.float64); ok = np.isfinite(a) & np.isfinite(b)
    return float(np.abs(a[ok] - b[ok]).max()) if ok.any() else 0.0
out = {"device": "ax10_prefix_proof.py", "self_sha256": sha(os.path.abspath(__file__)), "comparisons": {}}
T0 = time.time()
for c in SPEC:
    name, kind, mine, ref = c["name"], c["kind"], c["mine"], c["ref"]
    r = {"kind": kind, "mine": mine, "ref": ref, "mine_sha256": sha(mine), "ref_sha256": sha(ref)}
    print("==", name, flush=True)
    if kind == "targets":
        A = np.load(mine, allow_pickle=True); B = np.load(ref, allow_pickle=True)
        ea, eb = A["E_ts"].astype(np.int64), B["E_ts"].astype(np.int64)
        com, ia, ib = np.intersect1d(ea, eb, return_indices=True)
        r.update(n_mine=int(len(ea)), n_ref=int(len(eb)), n_common=int(len(com)), mine_first=U(ea[0]), mine_last=U(ea[-1]), ref_first=U(eb[0]), ref_last=U(eb[-1]),
                 ref_anchors_missing_in_mine=[U(t) for t in np.setdiff1d(eb, ea)][:30], n_ref_anchors_missing_in_mine=int(len(np.setdiff1d(eb, ea))))
        AM, BM = A["members"], B["members"]                      # materialise ONCE (NpzFile re-reads the whole array on every A[k] access)
        mem_eq = np.array([np.array_equal(np.asarray(AM[i], int), np.asarray(BM[j], int)) for i, j in zip(ia, ib)])
        nopan = (~B["has_panel"][ib]) & A["has_panel"][ia] if "has_panel" in B.files else np.zeros(len(com), bool)
        r["members_equal_anchors"] = int(mem_eq.sum()); r["members_differ_anchors"] = [U(t) for t in com[~mem_eq]][:30]; r["n_members_differ"] = int((~mem_eq).sum())
        r["ref_no_panel_row_anchors"] = [U(t) for t in com[nopan]]
        per = {}; unexpl = 0
        for k in ("y4s", "y4old", "qvk", "btcv", "YR4s", "YRZ", "has_panel", "yrs", "E_row"):
            if k not in A.files or k not in B.files: continue
            x, y = A[k][ia], B[k][ib]
            d = neq(x, y); dd = d.reshape(len(com), -1).any(1) if d.ndim > 1 else d
            cls_panel = dd & nopan; cls_other = dd & ~nopan
            panel_key = k in ("YR4s", "YRZ", "has_panel")
            per[k] = {"cells_compared": int(d.size), "cells_diff": int(d.sum()), "anchors_diff": int(dd.sum()), "maxabs": maxabs(x, y) if x.dtype.kind == "f" else None,
                      "anchors_diff_ref_no_panel_row": int(cls_panel.sum()), "anchors_diff_other": int(cls_other.sum()),
                      "anchors_diff_other_first": [U(t) for t in com[cls_other]][:20]}
            unexpl += int(cls_other.sum()) + (0 if panel_key else int(cls_panel.sum()))
        r["per_key"] = per; r["unexplained_anchor_diffs"] = unexpl + int((~mem_eq).sum())
    elif kind == "fea_long":
        A = np.load(mine, allow_pickle=True); B = np.load(ref, allow_pickle=True)
        TA = np.load(c["mine_targets"], allow_pickle=True); TB = np.load(c["ref_targets"], allow_pickle=True)
        ea, eb = TA["E_ts"].astype(np.int64), TB["E_ts"].astype(np.int64)
        com, ia, ib = np.intersect1d(ea, eb, return_indices=True)
        pa, pb = A["pair_a"].astype(np.int64), B["pair_a"].astype(np.int64)
        sa = np.searchsorted(pa, np.arange(len(ea) + 1)); sb = np.searchsorted(pb, np.arange(len(eb) + 1))
        names = [str(n) for n in A["names"]]; assert names == [str(n) for n in B["names"]], "feature names differ"
        nopan = (~TB["has_panel"][ib]) & TA["has_panel"][ia]
        fund_cols = [k for k, n in enumerate(names) if n.startswith("fund_")]
        XA, XB = A["X"], B["X"]; PSA, PSB = A["pair_s"], B["pair_s"]; nopan = np.asarray(nopan)
        coldiff = np.zeros(len(names), np.int64); anchors_diff_other = []; anchors_diff_panelonly = []; n_mem_diff = 0; cells = 0
        for k, (i, j) in enumerate(zip(ia, ib)):
            ra, rb = slice(sa[i], sa[i + 1]), slice(sb[j], sb[j + 1])
            if not np.array_equal(PSA[ra], PSB[rb]): n_mem_diff += 1; continue
            d = neq(XA[ra], XB[rb]); cells += d.size
            if d.any():
                cd = d.any(0); coldiff += d.sum(0)
                if nopan[k] and not cd[[q for q in range(len(names)) if q not in fund_cols]].any(): anchors_diff_panelonly.append(U(com[k]))
                else: anchors_diff_other.append((U(com[k]), [names[q] for q in np.nonzero(cd)[0]][:8]))
        r.update(n_common=int(len(com)), cells_compared=int(cells), anchors_members_differ=n_mem_diff, anchors_diff_ref_no_panel_fund_only=anchors_diff_panelonly,
                 anchors_diff_other=anchors_diff_other[:30], n_anchors_diff_other=len(anchors_diff_other),
                 columns_with_diff={names[q]: int(coldiff[q]) for q in np.nonzero(coldiff)[0]}, unexplained_anchor_diffs=len(anchors_diff_other) + n_mem_diff)
    elif kind == "king":
        MA = np.load(c["mine_meta"], allow_pickle=True); MB = np.load(c["ref_meta"], allow_pickle=True)
        ea, eb = MA["E_ts"].astype(np.int64), MB["E_ts"].astype(np.int64)
        com, ia, ib = np.intersect1d(ea, eb, return_indices=True)
        FA = np.load(mine, mmap_mode="r"); FB = np.load(ref, mmap_mode="r")
        names = [str(n) for n in MA["names"]]; fund_cols = [q for q, n in enumerate(names) if n.startswith("fund_")]
        MAM, MBM = MA["members"], MB["members"]                   # materialise ONCE
        # a reference anchor without a panel row has NaN fund columns for every member (the builder leaves them unset)
        coldiff = np.zeros(len(names), np.int64); other = []; fundonly = []; mem_diff = 0; cells = 0
        for k, (i, j) in enumerate(zip(ia, ib)):
            if not np.array_equal(np.asarray(MAM[i], int), np.asarray(MBM[j], int)): mem_diff += 1
            d = neq(np.asarray(FA[i]), np.asarray(FB[j])); cells += d.size
            if d.any():
                cd = d.any(0); coldiff += d.sum(0)
                refnopan = bool(np.isnan(np.asarray(FB[j])[np.asarray(MBM[j], int)][:, fund_cols]).all())
                if refnopan and not cd[[q for q in range(len(names)) if q not in fund_cols]].any(): fundonly.append(U(com[k]))
                else: other.append((U(com[k]), [names[q] for q in np.nonzero(cd)[0]][:8]))
        meta_eq = {k: {"anchors_diff": int(neq(MA[k][ia], MB[k][ib]).reshape(len(com), -1).any(1).sum()), "maxabs": maxabs(MA[k][ia], MB[k][ib])} for k in ("y4", "qvk")}
        r.update(n_mine=int(len(ea)), n_ref=int(len(eb)), n_common=int(len(com)), mine_first=U(ea[0]), mine_last=U(ea[-1]), ref_last=U(eb[-1]),
                 cells_compared=int(cells), members_differ_anchors=mem_diff, anchors_diff_ref_no_panel_fund_only=fundonly, anchors_diff_other=other[:30],
                 n_anchors_diff_other=len(other), columns_with_diff={names[q]: int(coldiff[q]) for q in np.nonzero(coldiff)[0]}, meta_keys=meta_eq,
                 unexplained_anchor_diffs=len(other) + mem_diff + sum(v["anchors_diff"] for v in meta_eq.values()))
    elif kind == "meta":
        A = np.load(mine, allow_pickle=True); B = np.load(ref, allow_pickle=True)
        ea, eb = A["E_ts"].astype(np.int64), B["E_ts"].astype(np.int64); com, ia, ib = np.intersect1d(ea, eb, return_indices=True)
        AM, BM = A["members"], B["members"]
        mem = np.array([np.array_equal(np.asarray(AM[i], int), np.asarray(BM[j], int)) for i, j in zip(ia, ib)])
        per = {k: {"anchors_diff": int(neq(A[k][ia], B[k][ib]).reshape(len(com), -1).any(1).sum()), "maxabs": maxabs(A[k][ia], B[k][ib])} for k in ("y4", "qvk")}
        r.update(n_mine=int(len(ea)), n_ref=int(len(eb)), n_common=int(len(com)), mine_last=U(ea[-1]), ref_last=U(eb[-1]), members_differ_anchors=int((~mem).sum()),
                 per_key=per, unexplained_anchor_diffs=int((~mem).sum()) + sum(v["anchors_diff"] for v in per.values()))
    elif kind == "mask":
        A = np.load(mine, allow_pickle=True); B = np.load(ref, allow_pickle=True)
        ta, tb = A["ts"].astype(np.int64), B["ts"].astype(np.int64); com, ia, ib = np.intersect1d(ta, tb, return_indices=True)
        assert [str(s) for s in A["symbols"]] == [str(s) for s in B["symbols"]]
        d = A["mask"][ia] != B["mask"][ib]
        r.update(n_mine=int(len(ta)), n_ref=int(len(tb)), n_common=int(len(com)), mine_last=U(ta[-1]), ref_last=U(tb[-1]), cells_diff=int(d.sum()),
                 anchors_diff=[U(t) for t in com[d.any(1)]][:30], unexplained_anchor_diffs=int(d.any(1).sum()))
    elif kind == "tradability":
        A = np.load(mine, allow_pickle=True); B = np.load(ref, allow_pickle=True)
        ta, tb = A["anchor_ts"].astype(np.int64), B["anchor_ts"].astype(np.int64); com, ia, ib = np.intersect1d(ta, tb, return_indices=True)
        per = {}
        for k in ("state_W24H", "state_W4H", "truncated_W24H", "truncated_W4H"):
            d = A[k][ia] != B[k][ib]; per[k] = {"cells_diff": int(d.sum()), "anchors_diff": [U(t) for t in com[d.reshape(len(com), -1).any(1)]][:20]}
        n5 = len(B["ts5"]); pre = {k: bool(np.array_equal(A[k][:n5], B[k])) for k in ("ts5", "traded5_bits", "nodata5_bits", "tradable5m_W24H_bits", "tradable5m_W4H_bits")}
        r.update(n_mine=int(len(ta)), n_ref=int(len(tb)), n_common=int(len(com)), mine_last=U(ta[-1]), ref_last=U(tb[-1]), per_key=per, bar_level_prefix_equal=pre,
                 unexplained_anchor_diffs=sum(len(v["anchors_diff"]) for k, v in per.items() if k.startswith("state")) + sum(0 if v else 1 for v in pre.values()))
    elif kind == "y4s":          # label-only identity against a build with a DIFFERENT member rule (all symbols, common anchors)
        A = np.load(mine, allow_pickle=True); B = np.load(ref, allow_pickle=True)
        ea, eb = A["E_ts"].astype(np.int64), B["E_ts"].astype(np.int64); com, ia, ib = np.intersect1d(ea, eb, return_indices=True)
        d = neq(A["y4s"][ia], B["y4s"][ib])
        r.update(n_common=int(len(com)), common_first=U(com[0]), common_last=U(com[-1]), cells_compared=int(d.size), cells_diff=int(d.sum()),
                 maxabs=maxabs(A["y4s"][ia], B["y4s"][ib]), anchors_diff=[U(t) for t in com[d.any(1)]][:30], unexplained_anchor_diffs=int(d.any(1).sum()))
    elif kind == "panel":        # 4h panel rows on common ts; keys named in expected_diff_keys may differ (the reference carries a KNOWN defect there)
        A = np.load(mine, allow_pickle=True); B = np.load(ref, allow_pickle=True)
        ta, tb = A["ts"].astype(np.int64), B["ts"].astype(np.int64); com, ia, ib = np.intersect1d(ta, tb, return_indices=True)
        lo = int(c.get("from_ts", 0)); sel = com >= lo; com, ia, ib = com[sel], ia[sel], ib[sel]
        exp = set(c.get("expected_diff_keys", [])); per = {}; unexpl = 0
        for k in sorted(set(A.files) & set(B.files) - {"ts", "symbols"}):
            x, y = A[k], B[k]
            if not (hasattr(x, "ndim") and x.ndim == 2 and len(x) == len(ta) and len(y) == len(tb)): continue
            d = neq(x[ia], y[ib]); na = int(d.any(1).sum())
            if d.any():
                per[k] = {"cells_diff": int(d.sum()), "anchors_diff": na, "symbols_diff": int(d.any(0).sum()), "maxabs": maxabs(x[ia], y[ib]),
                          "first_anchor": U(com[d.any(1)][0]), "symbols_first": [str(A["symbols"][q]) for q in np.nonzero(d.any(0))[0][:12]], "expected": k in exp}
                if k not in exp: unexpl += na
        r.update(n_mine=int(len(ta)), n_ref=int(len(tb)), n_common_compared=int(len(com)), compared_from=U(com[0]) if len(com) else None,
                 compared_to=U(com[-1]) if len(com) else None, keys_with_diff=per,
                 keys_compared=sorted(k for k in set(A.files) & set(B.files) - {"ts", "symbols"} if hasattr(A[k], "ndim") and A[k].ndim == 2 and len(A[k]) == len(ta)),
                 expected_diff_reason=c.get("expected_diff_reason"), unexplained_anchor_diffs=unexpl)
    r["PASS"] = r.get("unexplained_anchor_diffs", 1) == 0
    out["comparisons"][name] = r
    print(json.dumps(r, default=str)[:1500], flush=True)
out["VERDICT"] = {k: v["PASS"] for k, v in out["comparisons"].items()}; out["wall_s"] = round(time.time() - T0, 1)
json.dump(out, open(RPT, "w"), indent=1, default=str)
print("AX10_DONE", json.dumps(out["VERDICT"]), flush=True)
