"""R6 GATE BW-1 (PREREG §6.1): every PRE-EXISTING cell of the 5m cache must be BITWISE unchanged by the extension.
Read back from the WRITTEN FILE (not from the in-memory array that produced it) — a gate that trusts the producer's
own variable proves nothing (E-0909: 'patch on disk is not patch running').

Three statements per channel, all required:
  (1) NaN PATTERN bitwise equal            isnan(A) == isnan(B) everywhere
  (2) finite cells bitwise equal           A.view(uint16) == B.view(uint16) where finite  (float16 bit pattern, so
                                           -0.0 vs +0.0 and distinct NaN payloads cannot hide inside an '==' test)
  (3) np.array_equal(..., equal_nan=True)
Comparison set = 490753 x 829 x 7 = 2,847,839,659 cells (the FULL pre-existing grid, NaN included).
  NOTE the incumbent receipt's preexisting_equal = 1,114,912,699 is a DIFFERENT set: v4_hole_cells.py L?? compares
  holefix2 against _ext only where _ext is FINITE (`ok = np.isfinite(b)`), summed over 7 channels. It is not this
  gate's expected value and is not used as one (PREREG §6.1 hole, now RESOLVED by reading the source).
Also reports the §6.1a high-risk segment separately: rows 490465..490752 (2026-08-31 00:05..09-01 00:00), the day
holefix2 hole-filled 229,824 cells across 798 symbols.
"""
import numpy as np, zipfile, io, json, time, sys, os, hashlib
BASE = "/workspace/data/dlnative_5m_wide829_f16_holefix2.npz"
NEW  = os.environ.get("R6_OUT", "/workspace/data/dlnative_5m_wide829_f16_holefix2_x0910.npz")
RPT  = "/workspace/uplift_2026-09-11/r6/RECEIPT_BW1.json"
HR0, HR1 = 490465, 490752          # §6.1a high-risk rows (inclusive)
BLK = 20000

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""): h.update(ch)
    return h.hexdigest()

def opener(path, member):
    zf = zipfile.ZipFile(path); f = zf.open(member)
    ver = np.lib.format.read_magic(f)
    # numpy 2.x removed the private _read_array_header; dispatch on the .npy header version explicitly
    rd = {(1, 0): np.lib.format.read_array_header_1_0, (2, 0): np.lib.format.read_array_header_2_0}.get(ver)
    assert rd is not None, f"unsupported .npy header version {ver}"
    shape, fortran, dt = rd(f)
    assert not fortran
    return f, shape, dt

t0 = time.time()
fa, sa, da = opener(BASE, "data.npy")
fb, sb, db = opener(NEW, "data.npy")
assert da == db, (da, db)
assert sa[1:] == sb[1:], (sa, sb)
N0 = sa[0]
print(f"base data {sa} {da} | new data {sb} {db} | comparing first {N0} rows", flush=True)
rowsz = int(np.prod(sa[1:])) * da.itemsize
tot = N0 * int(np.prod(sa[1:]))
eq_nanpat = 0; eq_bits = 0; n_fin = 0; n_nan = 0; bad_rows = []
hr = {"rows": [HR0, HR1], "cells": 0, "finite": 0, "bits_equal": 0, "nanpat_equal": 0}
done = 0
while done < N0:
    n = min(BLK, N0 - done)
    A = np.frombuffer(fa.read(n*rowsz), dtype=da).reshape((n,)+sa[1:])
    B = np.frombuffer(fb.read(n*rowsz), dtype=db).reshape((n,)+sb[1:])
    ia, ib = np.isnan(A), np.isnan(B)
    same_pat = (ia == ib)
    eq_nanpat += int(same_pat.sum()); n_nan += int(ia.sum()); n_fin += int((~ia).sum())
    ua, ub = A.view(np.uint16), B.view(np.uint16)
    bits = (ua == ub)
    eq_bits += int(bits.sum())
    if not bits.all():
        br = np.unique(np.nonzero(~bits)[0]) + done
        bad_rows.extend(int(x) for x in br[:50])
    # high-risk segment
    lo, hi = max(done, HR0), min(done+n, HR1+1)
    if lo < hi:
        sl = slice(lo-done, hi-done)
        hr["cells"] += int(A[sl].size); hr["finite"] += int((~ia[sl]).sum())
        hr["bits_equal"] += int(bits[sl].sum()); hr["nanpat_equal"] += int(same_pat[sl].sum())
    done += n
    if done % 100000 < BLK: print(f"  {done}/{N0} ({time.time()-t0:.0f}s) bits_equal {eq_bits:,}", flush=True)
fa.close(); fb.close()

# ts / symbols / ch
za, zb = np.load(BASE, allow_pickle=True), np.load(NEW, allow_pickle=True)
ts_a, ts_b = za["ts"], zb["ts"]
ax = {"ts_prefix_bitwise_equal": bool(np.array_equal(ts_a, ts_b[:len(ts_a)])),
      "symbols_identical": bool([str(x) for x in za["symbols"]] == [str(x) for x in zb["symbols"]]),
      "ch_identical": bool([str(x) for x in za["ch"]] == [str(x) for x in zb["ch"]]),
      "new_rows": int(len(ts_b) - len(ts_a)),
      "new_end_utc": time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(int(ts_b[-1]))),
      "new_rows_step_300": bool(np.all(np.diff(ts_b.astype(np.int64)) == 300))}
rep = {"gate": "BW-1", "base": BASE, "base_sha256": sha(BASE), "new": NEW, "new_sha256": sha(NEW),
       "preexisting_cells_compared": int(tot), "expected_cells_arithmetic": int(N0*829*7),
       "nan_pattern_equal": int(eq_nanpat), "nan_pattern_diff": int(tot - eq_nanpat),
       "bitwise_equal": int(eq_bits), "bitwise_diff": int(tot - eq_bits),
       "n_finite_preexisting": int(n_fin), "n_nan_preexisting": int(n_nan),
       "first_bad_rows": bad_rows[:50], "high_risk_segment_2026_08_31": hr, "axes": ax,
       "wall_s": round(time.time()-t0, 1), "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
rep["verdict"] = "PASS" if (rep["bitwise_diff"] == 0 and rep["nan_pattern_diff"] == 0 and all(
    ax[k] for k in ("ts_prefix_bitwise_equal","symbols_identical","ch_identical","new_rows_step_300"))) else "FAIL"
json.dump(rep, open(RPT, "w"), indent=1)
print(json.dumps({k: rep[k] for k in ("gate","preexisting_cells_compared","bitwise_equal","bitwise_diff",
     "nan_pattern_diff","n_finite_preexisting","high_risk_segment_2026_08_31","axes","verdict")}, indent=1), flush=True)
print(f"BW1 {rep['verdict']}", flush=True)
sys.exit(0 if rep["verdict"] == "PASS" else 3)
