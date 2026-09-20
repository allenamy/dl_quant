#!/usr/bin/env python3
"""bt_objb_targets.py — ADAPTER: object-B target files → the history driver's book (W, fresh) and universe rows. Library only (numpy; no I/O
at import). Changes only WHERE the targets come from; everything downstream (target_doc → the executor's own parse_target → v3.1) is unchanged.

Format read (object_b_2026-09-19/devices/b_targets.py, commit da775552b; documented in its docstring and output block):
  TARGETS_<tag>.npz   anchor (int64, the P3 chain axis)
                      for each reading R ∈ {scaled (main, B-scaled), lit (B-lit, as coded), scaled_l333_only (sensitivity)}:
                        R_kind (int8, per anchor): 2 = the combo target file, 1 = the producer's king file (preflight failed / known crash),
                                                   0 = hold (producer skipped: NO new file; the executor's on_unavailable = hold carries the book)
                        R_off (int64, n+1) / R_idx (int16, column on the 829-symbol panel axis) / R_val (float): CSR rows = the file's weights
                                                   (empty on hold)
  receipts/TARGETS_<tag>.json   targets_npz_sha256, arm (A0 | V4), data (holefix2 | x0918r), axis, B_CORE_start, PRE_window, tag, …
Mapping (the same contract as stream R's S2 books): fresh[A] = kind ∈ {1, 2} ⇒ the adapter's target_doc writes the weights as a wide_target_v1
file (universe = the PIT row at A, the producer's symbols_live); kind 0 ⇒ no file ⇒ HOLD. The weights are passed as they are (the executor
normalises by Σ|w|); no re-weighting, no filtering.
VALIDATION (each violation raises TargetFormatError with a named reason; nothing is repaired or guessed):
  sha: npz == the pinned sha == receipt.targets_npz_sha256; receipt == its pinned sha; receipt.arm == the requested arm
  keys: anchor and all four arrays of the requested reading
  axis: int, strictly increasing on the 4h grid, contiguous; several sources (e.g. main + extension segment) must be disjoint and contiguous
        in the given order, of one arm; each source's data version is recorded
  CSR: len(off) = n+1, off[0] = 0, non-decreasing, off[-1] = len(idx) = len(val)
  rows: kind ∈ {0, 1, 2}; kind 0 ⇒ empty row; idx ∈ [0, n_sym); no duplicate column in a row; every value finite
  window: every simulated anchor is on the concatenated axis
Counted and reported (not refused): written rows with no weight (the driver's target_doc then writes no file ⇒ HOLD, counted as empty_target),
exact-zero weights, per-kind counts in the window.
"""
import hashlib, json, time

import numpy as np

H4 = 14400
READINGS = ("scaled", "lit", "scaled_l333_only")
MAIN_READING = "scaled"


class TargetFormatError(Exception):
    pass


def sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def _fail(reason, **kw):
    raise TargetFormatError(reason + ("" if not kw else " " + json.dumps(kw, default=str)[:300]))


def load_source(src, reading, arm, n_sym):
    """one TARGETS npz + its receipt → validated (anchor, kind, off, idx, val, info)"""
    if reading not in READINGS: _fail("unknown_reading", reading=reading)
    got = sha_file(src["npz"])
    if got != src["npz_sha256"]: _fail("npz_sha_mismatch_vs_pin", got=got[:16], want=src["npz_sha256"][:16])
    rs = sha_file(src["receipt"])
    if rs != src["receipt_sha256"]: _fail("receipt_sha_mismatch_vs_pin", got=rs[:16], want=src["receipt_sha256"][:16])
    R = json.load(open(src["receipt"]))
    if R.get("targets_npz_sha256") != got: _fail("npz_sha_mismatch_vs_receipt", receipt=str(R.get("targets_npz_sha256"))[:16], got=got[:16])
    if R.get("arm", "A0") != arm: _fail("arm_mismatch", receipt=R.get("arm"), want=arm)
    Z = np.load(src["npz"], allow_pickle=False)
    need = ["anchor"] + [f"{reading}_{k}" for k in ("kind", "off", "idx", "val")]
    miss = [k for k in need if k not in Z.files]
    if miss: _fail("missing_keys", missing=miss)
    A = np.asarray(Z["anchor"])
    if A.dtype.kind not in "iu": _fail("anchor_not_integer", dtype=str(A.dtype))
    A = A.astype(np.int64)
    if len(A) == 0: _fail("empty_axis")
    if np.any(A % H4 != 0): _fail("anchor_off_4h_grid", n=int(np.sum(A % H4 != 0)))
    if len(A) > 1 and not np.all(np.diff(A) == H4): _fail("axis_not_contiguous_4h", n_gaps=int(np.sum(np.diff(A) != H4)))
    kind = np.asarray(Z[f"{reading}_kind"]); off = np.asarray(Z[f"{reading}_off"]).astype(np.int64)
    idx = np.asarray(Z[f"{reading}_idx"]); val = np.asarray(Z[f"{reading}_val"]).astype(np.float64)
    if len(kind) != len(A): _fail("kind_length", kind=len(kind), anchors=len(A))
    if not np.all(np.isin(kind, (0, 1, 2))): _fail("kind_out_of_range", values=sorted(set(np.unique(kind).tolist()) - {0, 1, 2}))
    if len(off) != len(A) + 1 or off[0] != 0 or np.any(np.diff(off) < 0) or off[-1] != len(idx) or len(idx) != len(val):
        _fail("csr_offsets", len_off=len(off), n=len(A), off0=int(off[0]) if len(off) else None, last=int(off[-1]) if len(off) else None, n_idx=len(idx), n_val=len(val))
    if idx.dtype.kind not in "iu": _fail("idx_not_integer", dtype=str(idx.dtype))
    idx = idx.astype(np.int64)
    if len(idx) and (idx.min() < 0 or idx.max() >= n_sym): _fail("idx_out_of_range", lo=int(idx.min()), hi=int(idx.max()), n_sym=n_sym)
    if not np.all(np.isfinite(val)): _fail("non_finite_weight", n=int(np.sum(~np.isfinite(val))))
    rowlen = np.diff(off)
    if np.any((kind == 0) & (rowlen > 0)): _fail("hold_row_with_weights", n=int(np.sum((kind == 0) & (rowlen > 0))))
    for k in np.nonzero(rowlen > 1)[0]:
        r = idx[off[k]:off[k + 1]]
        if len(np.unique(r)) != len(r): _fail("duplicate_column_in_row", anchor=int(A[k]))
    info = dict(npz=src["npz"], npz_sha256=got, receipt=src["receipt"], receipt_sha256=rs, tag=R.get("tag"), arm=R.get("arm", "A0"), data=R.get("data"),
                axis=[int(A[0]), int(A[-1])], n=len(A), B_CORE_start=R.get("B_CORE_start"), PRE_window=R.get("PRE_window"),
                written_rows_without_weights=int(np.sum((kind > 0) & (rowlen == 0))), zero_weights=int(np.sum(val == 0.0)))
    return A, kind.astype(np.int8), off, idx, val, info


def load_targets(sources, reading=MAIN_READING, arm="A0", n_sym=829):
    """several sources (in axis order) → one validated target set"""
    if not sources: _fail("no_sources")
    parts = [load_source(s, reading, arm, n_sym) for s in sources]
    for (a0, *_), (a1, *_) in zip(parts[:-1], parts[1:]):
        if int(a1[0]) != int(a0[-1]) + H4: _fail("sources_not_contiguous_or_overlapping", end=int(a0[-1]), next_start=int(a1[0]))
    A = np.concatenate([p[0] for p in parts]); kind = np.concatenate([p[1] for p in parts])
    idx = np.concatenate([p[3] for p in parts]); val = np.concatenate([p[4] for p in parts])
    offs = [np.zeros(1, np.int64)]; base = 0
    for p in parts:
        offs.append(p[2][1:] + base); base += int(p[2][-1])
    off = np.concatenate(offs)
    return dict(anchor=A, kind=kind, off=off, idx=idx, val=val, reading=reading, arm=arm, sources=[p[5] for p in parts],
                B_CORE_start=[p[5]["B_CORE_start"] for p in parts])


def book_for_window(T, window_anchors, n_sym=829):
    """→ W (n_window × n_sym float64, the file weights), fresh (bool: a file is written), kind (int8), counts"""
    pos = {int(a): i for i, a in enumerate(T["anchor"])}
    ix = np.array([pos.get(int(a), -1) for a in window_anchors], np.int64)
    if np.any(ix < 0): _fail("window_anchor_not_in_targets_axis", n_missing=int(np.sum(ix < 0)), first_missing=int(np.asarray(window_anchors)[ix < 0][0]))
    W = np.zeros((len(ix), n_sym), np.float64); kind = T["kind"][ix]
    for r, k in enumerate(ix):
        a, b = T["off"][k], T["off"][k + 1]
        if b > a: W[r, T["idx"][a:b]] = T["val"][a:b]
    fresh = kind > 0
    counts = {"window_anchors": int(len(ix)), "combo": int(np.sum(kind == 2)), "king": int(np.sum(kind == 1)), "hold": int(np.sum(kind == 0)),
              "written_rows_without_weights": int(np.sum(fresh & (np.abs(W).sum(1) == 0)))}
    return W, fresh, kind, counts


def universe_rows(universe_npz, universe_sha, window_anchors, syms):
    """the PIT universe rows (the producer's symbols_live) for the target files; universe.npz / universe_ext.npz layout: ts, pit, symbols"""
    got = sha_file(universe_npz)
    if got != universe_sha: _fail("universe_sha_mismatch", got=got[:16], want=universe_sha[:16])
    U = np.load(universe_npz, allow_pickle=True)
    if [str(s) for s in U["symbols"]] != list(syms): _fail("universe_symbol_axis")
    row = {int(t): i for i, t in enumerate(np.asarray(U["ts"]).astype(np.int64))}
    ix = [row.get(int(a), -1) for a in window_anchors]
    if min(ix) < 0: _fail("window_anchor_not_in_universe_axis", n_missing=sum(1 for i in ix if i < 0))
    return np.asarray(U["pit"])[np.array(ix)].astype(bool)
