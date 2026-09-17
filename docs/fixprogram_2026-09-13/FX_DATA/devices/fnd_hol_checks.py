#!/usr/bin/env python3
"""fnd_hol_checks — the three checks of fx_fnd_hol_rebuild as PURE functions (FP2-1, 2026-09-17; independent review R16-D2).

Why this module exists. `fx_fnd_hol_rebuild.py` (sha pinned by its 09-16 receipts, untouched) carried three checks that could
be satisfied by the wrong thing:
  C1  compared klines with a RELATIVE 1e-6 tolerance: a 5e-7 change was invisible, and when the incumbent cell was ±Inf the
      threshold became Inf, so `|a-b| > Inf` was False for ANY rebuilt value — finite→Inf transitions passed; there was no
      finite-support gate at all.
  C2  copied all FIVE funding columns from the incumbent and recomputed only the three EMA columns, then compared each
      column to the incumbent: `f_fund_now` and `f_fund_iv` were compared with THEMSELVES.
  W   the write round-trip checked only the key list and the `ts` axis: X[0,0] := 999 in the written file still passed.
These functions replace them and are tested with synthetic arrays and NEGATIVE controls (finite→Inf, same values different
mask, one column written wrong, sub-tolerance perturbation). `fx_fnd_hol_rebuild_v2.py` calls them on the real panels.
"""
import numpy as np

# ── C1: exact difference mask with finite-support and NaN-mask agreement ────────────────────────────────────────────────
def c1_diff_mask(a, b):
    """Cells where the rebuild `a` differs from the incumbent `b` in ANY of: NaN mask, finite support (±Inf), or value (EXACT,
    no tolerance). Returns (mask, report). Away from hole neighbourhoods the caller requires mask.sum() == 0."""
    a = np.asarray(a, np.float64); b = np.asarray(b, np.float64)
    if a.shape != b.shape:
        raise ValueError(f"c1: shape mismatch {a.shape} vs {b.shape}")
    na, nb = np.isnan(a), np.isnan(b)
    fa, fb = np.isfinite(a), np.isfinite(b)
    both_finite = fa & fb
    val_diff = np.zeros(a.shape, bool)
    val_diff[both_finite] = a[both_finite] != b[both_finite]          # exact: the rebuild must be byte-equal away from holes
    mask = (na != nb) | (fa != fb) | val_diff
    rep = {"nan_mask_differs": int((na != nb).sum()), "finite_support_differs": int((fa != fb).sum()),
           "value_differs_exact": int(val_diff.sum()), "nonfinite_in_rebuild": int((~fa).sum()), "nonfinite_in_incumbent": int((~fb).sum()),
           "inf_in_rebuild": int((~fa & ~na).sum()), "inf_in_incumbent": int((~fb & ~nb).sum())}
    return mask, rep

# ── C2: rebuild ALL five funding columns from the event stream (no copy-then-compare) ───────────────────────────────────
ALLOWED_IV = np.array([1.0, 2.0, 4.0, 6.0, 8.0])
def c2_now_iv_from_stream(ft, fr, iv_full, tail_ts, stale_s=12 * 3600):
    """f_fund_now / f_fund_iv on the tail anchors, from the stream alone: the last event at or before the anchor, NaN when
    the last event is older than `stale_s` (r6_panel_splice.py L94–100 / pod_panel_ext.py L153–162)."""
    ft = np.asarray(ft, np.int64); fr = np.asarray(fr, np.float64); iv_full = np.asarray(iv_full, np.float64); tail_ts = np.asarray(tail_ts, np.int64)
    pos = np.searchsorted(ft, tail_ts, side="right") - 1; okp = pos >= 0
    fn = np.full(len(tail_ts), np.nan); fi = np.full(len(tail_ts), np.nan)
    fn[okp] = fr[pos[okp]]; fi[okp] = iv_full[pos[okp]]
    stale = okp & ((tail_ts - np.where(okp, ft[np.maximum(pos, 0)], 0)) > stale_s)
    fn[stale] = np.nan; fi[stale] = np.nan
    return fn.astype(np.float32), fi.astype(np.float32)

def c2_compare_columns(rebuilt, incumbent, columns, rebuilt_from_stream):
    """Per-column independent comparison. `rebuilt_from_stream` names the columns that were actually RECOMPUTED (not copied);
    a column that is not in it is reported as SELF_COMPARE and can never count as reproduced."""
    out = {}
    for c in columns:
        a = np.asarray(rebuilt[c], np.float64); b = np.asarray(incumbent[c], np.float64)
        na, nb = np.isnan(a), np.isnan(b)
        bitwise = bool(a.shape == b.shape and np.array_equal(na, nb) and a[~na].tobytes() == b[~nb].tobytes())
        out[c] = {"recomputed": c in rebuilt_from_stream, "nan_equal": bool(a.shape == b.shape and np.array_equal(na, nb)),
                  "bitwise": bitwise if c in rebuilt_from_stream else False,
                  "verdict": ("REPRODUCED" if (c in rebuilt_from_stream and bitwise) else "SELF_COMPARE" if c not in rebuilt_from_stream else "DIFFERS"),
                  "maxabs": float(np.abs(a[~na & ~nb] - b[~na & ~nb]).max()) if a.shape == b.shape and (~na & ~nb).any() else None}
    return out

# ── W: write round-trip over EVERY array's payload ──────────────────────────────────────────────────────────────────────
def roundtrip_verify(loaded, expected):
    """`loaded` = np.load(path) (or dict), `expected` = the dict that was written. Every key: present, dtype, shape, NaN mask
    and bytes equal. Returns (ok, report) — a single differing cell in any array is a FAIL."""
    rep = {"keys_missing": sorted(set(expected) - set(getattr(loaded, "files", loaded.keys()))),
           "keys_extra": sorted(set(getattr(loaded, "files", loaded.keys())) - set(expected)), "per_key": {}}
    ok = not rep["keys_missing"] and not rep["keys_extra"]
    for k in expected:
        if k in rep["keys_missing"]: continue
        a = np.asarray(loaded[k]); b = np.asarray(expected[k])
        r = {"dtype_equal": a.dtype == b.dtype, "shape_equal": a.shape == b.shape}
        if r["dtype_equal"] and r["shape_equal"]:
            if a.dtype.kind in "fc":
                na, nb = np.isnan(a), np.isnan(b); r["nan_mask_equal"] = bool(np.array_equal(na, nb))
                r["bytes_equal"] = bool(r["nan_mask_equal"] and a[~na].tobytes() == b[~nb].tobytes())
            else:
                r["nan_mask_equal"] = True; r["bytes_equal"] = bool(a.tobytes() == b.tobytes())
        else:
            r["nan_mask_equal"] = False; r["bytes_equal"] = False
        r["ok"] = bool(r["dtype_equal"] and r["shape_equal"] and r["nan_mask_equal"] and r["bytes_equal"])
        rep["per_key"][k] = r; ok = ok and r["ok"]
    rep["n_keys_bad"] = sum(1 for r in rep["per_key"].values() if not r["ok"])
    return ok, rep

# ── F05 (independent review 2026-09-17): names WITHOUT a source stream are NOT rebuilt — they are carried from the incumbent and must never be
#    counted as REPRODUCED. The caller passes the per-symbol source mask; the comparison runs on sourced symbols only and the receipt names the rest.
def c2_compare_columns_sourced(rebuilt, incumbent, columns, rebuilt_from_stream, has_source):
    """`has_source`: boolean per symbol column (axis 1). Returns (per-column verdicts over sourced symbols, no_source summary)."""
    hs = np.asarray(has_source, bool)
    sub_r = {c: np.asarray(rebuilt[c])[:, hs] for c in columns}; sub_i = {c: np.asarray(incumbent[c])[:, hs] for c in columns}
    res = c2_compare_columns(sub_r, sub_i, columns, rebuilt_from_stream) if hs.any() else {c: {"recomputed": False, "bitwise": False, "verdict": "UNAVAILABLE_NO_SOURCED_SYMBOL", "maxabs": None, "nan_equal": None} for c in columns}
    ns = {"n_symbols": int(hs.size), "n_with_source": int(hs.sum()), "n_no_source": int((~hs).sum()), "no_source_idx": np.nonzero(~hs)[0].tolist(),
          "verdict_no_source": "COPIED_NO_SOURCE" if (~hs).any() else "NONE", "independent_rebuild_partial": bool((~hs).any())}
    for c in columns: res[c]["symbols_compared"] = int(hs.sum()); res[c]["symbols_copied_no_source"] = int((~hs).sum())
    return res, ns
