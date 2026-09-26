"""The producer's member rule as a function (gap class fix 2026-09-26, ACCEPTANCE AMENDMENT 2).

Body = shadow_loop_v3.py (sha 52baf979…) L676-L701 verbatim, with `st.cts / st.cd / st.crypto / st.fetch_mask / anchor / ai` as arguments
and CDf = st.cd.astype(np.float32) (L660; channel 0 is the f16 STORAGE, not rr). Used by combo_stage to recompute the member set of an anchor
the producer never ran (members_hist has no entry) instead of treating it as "no members" (which zeroes f8 drank_*_1d 24 h later).
The fetch mask of a past anchor is not recorded; the caller passes the one in force at the current anchor (aux.fetch_syms minus
nc_backfill_residual) — the accuracy of that approximation is measured by members_rule_validate.py (V2)."""
import numpy as np


def members_at(cts, cd, anchor, crypto, fetch_mask, P, TR, NC):
    """cd = the float16 storage (st.cd); CDf below = its float32 cast, sliced first (identical values to casting the whole cache)."""
    cts = np.asarray(cts, np.int64)
    ai = int(np.searchsorted(cts, anchor, side="right")) - 1
    if ai < 0 or cts[ai] != anchor:
        raise ValueError(f"anchor {anchor} is not a row of the rolling cache")
    _w0 = max(ai + 1 - 2016, 0)
    CDf = np.asarray(cd[_w0:ai + 1]).astype(np.float32)   # L660 st.cd.astype(np.float32), window rows only
    # 成员筛
    r5seg = CDf[:, :, 0]
    fin5 = np.isfinite(r5seg)
    covr = fin5.sum(0) / 2016
    c7 = fin5.sum(0)
    n7 = np.maximum(c7, 1)
    z5 = np.where(fin5, r5seg, 0).astype(np.float64)        # NEW_S2 D5
    m7 = z5.sum(0)
    v7 = np.sqrt(np.maximum((z5 * z5).sum(0) / n7 - (m7 / n7) ** 2, 0))
    del z5
    v7 = np.where(c7 > 0, v7, np.nan).astype(np.float32)   # NEW_S2 D6
    qseg = CDf[:, :, 3]
    finq = np.isfinite(qseg)
    cq = finq.sum(0)
    qvm = np.where(finq, qseg, 0).sum(0, dtype=np.float64) / np.maximum(cq, 1)
    qvm = np.where(cq > 0, qvm, np.nan).astype(np.float32)   # NEW_S2 D6
    # NC A1: candidates = legal (TRADABLE W24H ∧ live, nc_contract.legal_live) ∧ crypto ∧ fetched at this anchor
    _lo24 = max(ai - 290, 0)
    legal_now = NC.legal_live(cts[_lo24:ai + 1], cd[_lo24:ai + 1, :, 4], cd[_lo24:ai + 1, :, 3], [anchor], TR)[0]
    cand_now = legal_now & crypto & fetch_mask
    ok = cand_now & (covr >= P["cov_min"]) & (v7 >= P["vol_min"])
    assert not np.any(ok & ~np.isfinite(qvm)), "NEW_S2 D6: member passes cov/vol but qvm window is empty"
    m = np.where(ok)[0]
    if len(m) > P["NTOP"]:
        m = np.sort(m[np.argsort(-qvm[m], kind="stable")[:P["NTOP"]]])   # NEW_S2 D14 (feature_contract.select_members)
    return m.astype(np.int64)


def fetch_mask_from_aux(aux, syms):
    """the fetch mask in force at aux's anchor: fetch_syms minus the named backfill residual (shadow_loop_v3 L547 / L561)."""
    sym_idx = {s: j for j, s in enumerate(syms)}
    fm = np.zeros(len(syms), bool)
    fm[[sym_idx[s] for s in aux["fetch_syms"] if s in sym_idx]] = True
    for s in aux.get("nc_backfill_residual") or []:
        if s in sym_idx:
            fm[sym_idx[s]] = False
    return fm
