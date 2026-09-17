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
def c2_compare_columns_sourced(rebuilt, incumbent, columns, rebuilt_from_stream, has_source, source_symbols=None):
    """`has_source` = which cells were actually REBUILT and may be compared:
         · one boolean vector over symbols (axis 1)  → applied to every column, every row;
         · a dict {column: boolean vector (N,) or boolean matrix (T, N)} → per column, optionally per cell (R02, independent review
           2026-09-17: a name WITH a funding stream but WITHOUT the canonical EMA seed is skipped by the verbatim block, so its three
           EMA columns are incumbent copies; with a missing v2 seed only the rows before the first tail event are copies).
       `source_symbols` (N,) = which names have a stream at all (default: the 1-D mask, or any-cell-rebuilt per name for a dict).
       A cell outside the mask is never compared. Verdicts per column: REPRODUCED (≥1 cell compared, all bitwise equal incl. NaN pattern),
       DIFFERS, UNAVAILABLE_NO_SOURCED_SYMBOL (no cell to compare). Returns (per-column verdicts, summary)."""
    cols = list(columns)
    T, N = np.asarray(rebuilt[cols[0]]).shape
    def cell_mask(m):
        m = np.asarray(m, bool)
        if m.ndim == 1:
            assert m.shape == (N,), ("mask over symbols must be (N,)", m.shape, N)
            return np.broadcast_to(m[None, :], (T, N)).copy()
        assert m.shape == (T, N), ("cell mask must be (T, N)", m.shape, (T, N)); return m.copy()
    if isinstance(has_source, dict): masks = {c: cell_mask(has_source[c]) for c in cols}
    else: masks = {c: cell_mask(has_source) for c in cols}
    if source_symbols is None:
        source_symbols = np.asarray(has_source, bool) if not isinstance(has_source, dict) else np.any([masks[c].any(0) for c in cols], axis=0)
    src = np.asarray(source_symbols, bool); assert src.shape == (N,)
    res = {}; ns = {"n_symbols": int(N), "n_with_source": int(src.sum()), "n_no_source": int((~src).sum()), "no_source_idx": np.nonzero(~src)[0].tolist(),
                    "verdict_no_source": "COPIED_NO_SOURCE" if (~src).any() else "NONE", "copied_no_seed_idx": {}, "partial_idx": {}}
    partial = bool((~src).any())
    for c in cols:
        M = masks[c]; a = np.asarray(rebuilt[c], np.float64); b = np.asarray(incumbent[c], np.float64)
        assert a.shape == b.shape == (T, N), (c, a.shape, b.shape)
        na, nb = np.isnan(a), np.isnan(b)
        n_cells = int(M.sum())
        if n_cells == 0:
            eq = False; verdict = "UNAVAILABLE_NO_SOURCED_SYMBOL"; maxabs = None; nan_eq = None
        else:
            nan_eq = bool(np.array_equal(na[M], nb[M])); fin = M & ~na & ~nb
            eq = bool(nan_eq and a[fin].tobytes() == b[fin].tobytes())
            verdict = "REPRODUCED" if (c in rebuilt_from_stream and eq) else ("SELF_COMPARE" if c not in rebuilt_from_stream else "DIFFERS")
            maxabs = float(np.abs(a[fin] - b[fin]).max()) if fin.any() else 0.0
        per_sym = M.sum(0)                                   # compared cells per name
        fully = per_sym == T; some = (per_sym > 0) & ~fully; none_ = per_sym == 0
        no_seed = src & none_; part = src & some
        res[c] = {"recomputed": c in rebuilt_from_stream, "bitwise": eq if c in rebuilt_from_stream else False, "nan_equal": nan_eq, "verdict": verdict, "maxabs": maxabs,
                  "cells_compared": n_cells, "cells_copied": int(M.size - n_cells), "symbols_compared": int((per_sym > 0).sum()), "symbols_fully_compared": int(fully.sum()),
                  "symbols_partially_compared": int(part.sum()), "symbols_copied_no_source": int((~src).sum()), "symbols_copied_no_seed": int(no_seed.sum())}
        ns["copied_no_seed_idx"][c] = np.nonzero(no_seed)[0].tolist(); ns["partial_idx"][c] = np.nonzero(part)[0].tolist()
        if no_seed.any() or part.any(): partial = True
    ns["independent_rebuild_partial"] = bool(partial)
    return res, ns

# ── R02 instrumentation: observe which cells a verbatim block WROTE (a NaN with a non-canonical payload nothing the block computes can produce) ──
def nan_sentinel(dtype):
    dtype = np.dtype(dtype)
    if dtype == np.float32: return np.array([0x7fc00001], np.uint32).view(np.float32)[0]
    if dtype == np.float64: return np.array([0x7ff8000000000001], np.uint64).view(np.float64)[0]
    raise SystemExit(f"UNAVAILABLE: unexpected panel dtype {dtype}")
def float_bits(a):
    a = np.ascontiguousarray(a); return a.view(np.uint32 if a.dtype == np.float32 else np.uint64)
def written_cells(col):
    """True where `col` no longer holds the sentinel it was filled with before the block ran."""
    return float_bits(col) != float_bits(np.array([nan_sentinel(col.dtype)], col.dtype))[0]
