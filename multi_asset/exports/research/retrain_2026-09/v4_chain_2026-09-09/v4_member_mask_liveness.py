#!/usr/bin/env python3
"""v4_member_mask_liveness.py — MEMBER_LIVENESS enforcement, BUILD side (FP3 F; ELIGIBILITY_CONTRACT rules MEMBER_LIVENESS, applied 2026-09-18
by the user's word 「按最佳建议来」; the gate side is v4_gate_member_liveness.py, which re-derives the rule from the produced builds without this mask).

Builds the TRAINING MEMBER MASK on the 5m cache's own 4h grid:
    mask[A, s] = True  iff  name s has at least one REAL 5-minute bar in the 288 rows ending at the anchor row
                            (rows (r-288, r], r = the cache row whose ts == A),
    real = NOT a hole-filled cell (HOLE_CELLS row/col list) AND log_qv (cache channel 3) finite.
Same window and definition as the measuring device fx_member_liveness.py (FX_DATA/receipts/MEMBER_LIVENESS_2026-09-18.json). Optionally ANDed
with an input mask (MASK_IN, e.g. the FP2-8 tradable-W24H mask on the same grid): the output is then tradable AND live. The builders
(pod_fea_ext_clamp_v2.py / pod_dlw_targets_raw_v2.py) consume the output as MEMBER_MASK_NPZ = their own rule AND this mask.

Boundary (independent review r7): a real bar with zero trades is LIVE — data liveness, not venue eligibility truth.
Window convention: rows (r-W, r] include the bar whose open ts == A (as in the measuring device), W = 86400 / the cache's own uniform
row spacing (R12-C4: a hard-coded 288 covers 48 h on a 600 s grid). Anchors with fewer than W rows of history
use the rows available (the builders' own TRAIL=2016 rule drops those anchors anyway); their count is reported as n_short_window.

Positive control BEFORE anything is written (three-state):
  C0  cache ts strictly increasing and the 4h grid non-empty (ts integrality checked before any cast)
  C0b cache row spacing uniform and dividing the 24 h window
  C1  cache channel 3 is named log_qv
  C2  HOLE_CELLS symbols axis == cache symbols; every (row, col) inside the cache
  C3  (MASK_IN given) MASK_IN sha == MASK_IN_SHA; symbols == cache symbols; bool [T, N]; every grid anchor has a MASK_IN row
  W1  re-read == written (mask, ts, symbols)
FAIL ⇒ nothing written (a failed W1 removes the file), rc 1; an input that cannot be read ⇒ UNAVAILABLE, rc 3; PASS ⇒ rc 0.
env: CACHE HOLE_CELLS OUT RECEIPT (required); MASK_IN MASK_IN_SHA (optional, both or neither)."""
import hashlib, json, os, sys, time, zipfile
import numpy as np

WINDOW_SECONDS = 86400       # the rule's window is 24 HOURS; the row count is derived from the cache's own spacing (R12-C4)
LOG_QV_CH = 3                # the cache channel the rule reads (checked by name in C1)
ANCHOR_SECONDS = 14400
DEVICE = "v4_member_mask_liveness.py"


def int_axis(arr, name):
    """(int64 values, error-or-None) — integrality checked BEFORE the cast; same helper as the gate (R12-C4)."""
    a = np.asarray(arr)
    if a.dtype.kind in "iu":
        return a.astype(np.int64), None
    if a.dtype.kind == "b":
        return None, f"{name}: boolean dtype is not a timestamp axis"
    if a.dtype.kind == "f":
        if a.size and not np.all(np.isfinite(a)):
            return None, f"{name}: float axis carries non-finite values"
        if a.size and not np.all(a == np.rint(a)):
            return None, f"{name}: float axis with non-integral values; casting would silently truncate"
        return a.astype(np.int64), None
    return None, f"{name}: dtype {a.dtype} is not an integer axis"


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""):
            h.update(ch)
    return h.hexdigest()


def det_npz(path, arrays):   # deterministic writer (= fp2_member_mask_build.py det_npz): fixed date, sorted keys, no pickle
    tmp = path + ".tmp"
    with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for k in sorted(arrays):
            zi = zipfile.ZipInfo(k + ".npy", date_time=(1980, 1, 1, 0, 0, 0)); zi.compress_type = zipfile.ZIP_DEFLATED
            a = np.asarray(arrays[k]); a = a if a.ndim == 0 else np.ascontiguousarray(a)
            with zf.open(zi, "w", force_zip64=True) as fh:
                np.lib.format.write_array(fh, a, allow_pickle=False)
    os.replace(tmp, path)


def load_channel(cache_path, ch_idx):
    """One channel of the cache's `data` array as float32 without materialising the whole (T, N, C) array: an uncompressed (STORED) member
    is memory-mapped at its offset inside the zip; a compressed member falls back to np.load (the measuring device's way)."""
    with zipfile.ZipFile(cache_path) as z:
        zi = z.getinfo("data.npy")
        if zi.compress_type == zipfile.ZIP_STORED:
            with z.open(zi) as fh:
                version = np.lib.format.read_magic(fh)
                rdr = {(1, 0): np.lib.format.read_array_header_1_0, (2, 0): np.lib.format.read_array_header_2_0}.get(tuple(version))
                if rdr is None: raise ValueError(f"unsupported .npy header version {version}")   # public API: numpy renamed the private _read_array_header
                shape, fortran, dtype = rdr(fh)
                hdr_len = fh.tell()
            with open(cache_path, "rb") as raw:
                raw.seek(zi.header_offset)
                fixed = raw.read(30)                                           # local file header: 30 fixed bytes + name + extra
                n_name = int.from_bytes(fixed[26:28], "little"); n_extra = int.from_bytes(fixed[28:30], "little")
                data_off = zi.header_offset + 30 + n_name + n_extra + hdr_len
            if fortran or len(shape) != 3:
                raise ValueError(f"cache data.npy shape/order unsupported: {shape} fortran={fortran}")
            mm = np.memmap(cache_path, dtype=dtype, mode="r", offset=data_off, shape=tuple(shape))
            return np.ascontiguousarray(mm[:, :, ch_idx]).astype(np.float32), tuple(shape)
    C = np.load(cache_path, allow_pickle=True)
    d = C["data"]
    return d[:, :, ch_idx].astype(np.float32), tuple(d.shape)


def main():
    E = {k: os.environ.get(k, "") for k in ("CACHE", "HOLE_CELLS", "OUT", "RECEIPT", "MASK_IN", "MASK_IN_SHA")}
    rec = {"device": DEVICE, "self_sha256": sha(os.path.abspath(__file__)), "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "env": dict(E), "rule": "MEMBER_LIVENESS", "window_seconds": WINDOW_SECONDS, "window_rows": None, "row_spacing_s": None, "checks": {}, "VERDICT": None}

    def write_receipt():
        if E["RECEIPT"]:
            os.makedirs(os.path.dirname(os.path.abspath(E["RECEIPT"])), exist_ok=True)
            json.dump(rec, open(E["RECEIPT"], "w"), indent=1, default=str)

    def unavailable(msg):
        rec["VERDICT"] = "UNAVAILABLE"; rec["error"] = msg; write_receipt(); print("UNAVAILABLE", msg, flush=True); return 3

    def check(name, ok, detail=None):
        rec["checks"][name] = {"ok": bool(ok), "detail": detail}
        print(("  OK   " if ok else "  FAIL ") + name + (("  — " + json.dumps(detail, default=str)[:220]) if detail is not None else ""), flush=True)

    missing = [k for k in ("CACHE", "HOLE_CELLS", "OUT", "RECEIPT") if not E[k]]
    if missing:
        return unavailable(f"env missing {missing}")
    if bool(E["MASK_IN"]) != bool(E["MASK_IN_SHA"]):
        return unavailable("MASK_IN and MASK_IN_SHA must be given together (an unpinned input mask is not an input)")
    try:
        C = np.load(E["CACHE"], allow_pickle=True)
        cts, _e = int_axis(C["ts"], "cache ts")
        if _e: return unavailable(_e)
        csym = [str(s) for s in C["symbols"]]; ch = [str(x) for x in C["ch"]]
        lq, dshape = load_channel(E["CACHE"], LOG_QV_CH)
        H = np.load(E["HOLE_CELLS"], allow_pickle=True)
        hrow, _e1 = int_axis(H["row"], "hole cells row"); hcol, _e2 = int_axis(H["col"], "hole cells col")
        if _e1 or _e2: return unavailable(_e1 or _e2)
        hsym = [str(s) for s in H["symbols"]]
        cache_sha = sha(E["CACHE"]); holes_sha = sha(E["HOLE_CELLS"])
        MI = mts = msym = MM = None; mi_sha = ""
        if E["MASK_IN"]:
            mi_sha = sha(E["MASK_IN"]); MI = np.load(E["MASK_IN"], allow_pickle=True)
            mts, _e3 = int_axis(MI["ts"], "MASK_IN ts")
            if _e3: return unavailable(_e3)
            msym = [str(s) for s in MI["symbols"]]; MM = np.asarray(MI["mask"])
    except Exception as e:   # noqa: BLE001
        return unavailable(repr(e))
    nT, nS = lq.shape
    rec["inputs"] = {"cache": E["CACHE"], "cache_sha256": cache_sha, "hole_cells": E["HOLE_CELLS"], "hole_cells_sha256": holes_sha,
                     "mask_in": E["MASK_IN"] or None, "mask_in_sha256": mi_sha or None, "cache_shape": list(dshape), "n_hole_cells": int(len(hrow)),
                     "window_seconds": WINDOW_SECONDS}
    on_grid = (cts % ANCHOR_SECONDS == 0)
    grid = cts[on_grid]; grid_rows = np.nonzero(on_grid)[0]
    check("C0 cache ts strictly increasing, 4h grid non-empty, ts axis == data rows",
          bool(len(cts) == nT and len(csym) == nS and len(grid) > 0 and np.all(np.diff(cts) > 0)),
          {"n_rows": int(nT), "n_symbols": int(nS), "n_grid": int(len(grid))})
    # ★ R12-C4: W comes from the cache's own uniform spacing, not a hard-coded 288 (which is 24 h only on a 300 s grid)
    W = None; _dts = np.unique(np.diff(cts)) if len(cts) > 1 else np.array([])
    _uniform = len(_dts) == 1 and int(_dts[0]) > 0 and WINDOW_SECONDS % int(_dts[0]) == 0
    if _uniform: W = WINDOW_SECONDS // int(_dts[0]); rec["window_rows"] = int(W); rec["row_spacing_s"] = int(_dts[0])
    check("C0b cache row spacing is uniform and divides the 24 h window",
          bool(_uniform), {"n_distinct_steps": int(len(_dts)), "step_s": (int(_dts[0]) if len(_dts) == 1 else None), "window_rows": (int(W) if W else None)})
    check("C1 cache channel 3 is log_qv", len(ch) > LOG_QV_CH and ch[LOG_QV_CH] == "log_qv", {"channels": ch})
    check("C2 hole cells: symbols axis == cache; every (row, col) inside the cache",
          hsym == csym and (len(hrow) == 0 or (int(hrow.min()) >= 0 and int(hrow.max()) < nT and int(hcol.min()) >= 0 and int(hcol.max()) < nS)),
          {"n_cells": int(len(hrow)), "symbols_equal": hsym == csym})
    if MI is not None:
        pos = {int(t): i for i, t in enumerate(mts)}
        miss = [int(t) for t in grid if int(t) not in pos]
        check("C3 MASK_IN: sha == declared, symbols == cache, bool [T, N], every grid anchor has a row",
              mi_sha == E["MASK_IN_SHA"] and msym == csym and MM.dtype == np.bool_ and MM.ndim == 2 and MM.shape == (len(mts), nS) and not miss,
              {"sha_ok": mi_sha == E["MASK_IN_SHA"], "symbols_equal": msym == csym, "dtype": str(MM.dtype), "shape": list(MM.shape), "n_missing_anchors": len(miss),
               "definition": str(MI["definition"]) if "definition" in MI.files else None})
    if any(not c["ok"] for c in rec["checks"].values()):
        rec["VERDICT"] = "FAIL"; write_receipt(); print("FAIL (nothing written)", flush=True); return 1

    notlive = ~np.isfinite(lq)
    if len(hrow):
        notlive[hrow, hcol] = True
    cs = np.zeros((nT + 1, nS), np.int32); np.cumsum(notlive, axis=0, dtype=np.int32, out=cs[1:])
    hi = grid_rows + 1; lo = np.maximum(hi - W, 0)
    cnt = cs[hi] - cs[lo]; avail = (hi - lo)[:, None]
    live = cnt < avail                                          # at least one live row among the rows available
    n_short = int((hi - lo < W).sum())
    mask = live.copy()
    removed_beyond_in = None
    if MI is not None:
        inrows = MM[[pos[int(t)] for t in grid]]
        removed_beyond_in = int((inrows & ~live).sum())        # cells the input mask kept that liveness removes
        mask &= inrows
    years = np.array([time.gmtime(int(t)).tm_year for t in grid])
    by_year = {}
    for y in sorted(set(years.tolist())):
        sel = years == y
        by_year[str(y)] = {"n_anchors": int(sel.sum()), "live_frac": round(float(live[sel].mean()), 6), "mask_frac": round(float(mask[sel].mean()), 6)}
    rec["result"] = {"n_grid": int(len(grid)), "grid_first": int(grid[0]), "grid_last": int(grid[-1]), "n_short_window": n_short,
                     "window_rows": int(W), "row_spacing_s": int(_dts[0]),
                     "live_cells": int(live.sum()), "mask_cells": int(mask.sum()), "cells_removed_beyond_mask_in": removed_beyond_in, "by_year": by_year}
    definition = (f"MEMBER_LIVENESS: at least one REAL bar (not hole-filled, log_qv finite) in the {WINDOW_SECONDS}s window ending at the anchor row (rows (r-{W}, r], spacing {int(_dts[0])}s); "
                  + ("AND MASK_IN " + mi_sha[:16] if MI is not None else "no input mask") + "; on the 5m cache 4h grid; training member mask")
    arrays = {"ts": grid.astype(np.int64), "symbols": np.array(csym), "mask": mask.astype(np.bool_), "definition": np.array(definition),
              "rule": np.array("MEMBER_LIVENESS"), "window_rows": np.array(W, np.int64), "window_seconds": np.array(WINDOW_SECONDS, np.int64),
              "row_spacing_s": np.array(int(_dts[0]), np.int64), "cache_sha256": np.array(cache_sha), "holes_sha256": np.array(holes_sha),
              "mask_in_sha256": np.array(mi_sha), "device_sha256": np.array(rec["self_sha256"])}
    os.makedirs(os.path.dirname(os.path.abspath(E["OUT"])), exist_ok=True)
    det_npz(E["OUT"], arrays)
    back = np.load(E["OUT"], allow_pickle=True)
    w1 = bool(np.array_equal(back["mask"], mask) and np.array_equal(back["ts"].astype(np.int64), grid) and [str(s) for s in back["symbols"]] == csym)
    check("W1 re-read == written (mask, ts, symbols)", w1)
    if not w1:
        os.remove(E["OUT"]); rec["VERDICT"] = "FAIL"; write_receipt(); print("FAIL (output removed)", flush=True); return 1
    rec["out"] = E["OUT"]; rec["out_sha256"] = sha(E["OUT"]); rec["VERDICT"] = "PASS"; write_receipt()
    print(f"PASS mask {E['OUT']} sha {rec['out_sha256'][:16]} grid {len(grid)} live_cells {int(live.sum())} mask_cells {int(mask.sum())} "
          f"removed_beyond_mask_in {removed_beyond_in} short_window {n_short}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
