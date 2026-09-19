"""AX03b (axis_0919): GATE BW (append-only) for the extended 5m cache — generalisation of r6_bw1_gate.py (same three statements, same streaming reader),
run against EVERY base in AX_BASES (comma list, e.g. holefix2 canon and x0910), re-read from the WRITTEN files.
Per base: (1) NaN pattern equal, (2) finite cells bitwise equal as uint16, (3) ts prefix / symbols / ch identical; plus max |delta| on cells finite in both
(0.0 when (2) holds) and the count of cells compared = rows_base x 829 x 7 (FULL pre-existing grid, NaN included).
env: AX_NEW, AX_BASES, AX_RECEIPT.  rc 0 = PASS for every base, 3 = FAIL.
"""
import numpy as np, zipfile, json, time, sys, os, hashlib
NEW = os.environ["AX_NEW"]; BASES = [b for b in os.environ["AX_BASES"].split(",") if b]; RPT = os.environ["AX_RECEIPT"]
assert not os.path.exists(RPT), "refuse to overwrite receipt"
BLK = 20000
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""): h.update(ch)
    return h.hexdigest()
def opener(path, member):
    zf = zipfile.ZipFile(path); f = zf.open(member)
    ver = np.lib.format.read_magic(f)
    rd = {(1, 0): np.lib.format.read_array_header_1_0, (2, 0): np.lib.format.read_array_header_2_0}.get(ver)
    assert rd is not None, f"unsupported .npy header version {ver}"
    shape, fortran, dt = rd(f); assert not fortran
    return f, shape, dt
t0 = time.time()
rep = {"gate": "BW (append-only, bitwise)", "device": "ax03b_bw_gate.py", "self_sha256": sha(os.path.abspath(__file__)), "new": NEW, "new_sha256": sha(NEW), "per_base": {}}
zb = np.load(NEW, allow_pickle=True); ts_b = zb["ts"].astype(np.int64)
for BASE in BASES:
    fa, sa, da = opener(BASE, "data.npy"); fb, sb, db = opener(NEW, "data.npy")
    assert da == db and sa[1:] == sb[1:], (da, db, sa, sb)
    N0 = sa[0]; rowsz = int(np.prod(sa[1:])) * da.itemsize; tot = N0 * int(np.prod(sa[1:]))
    eq_nanpat = eq_bits = n_fin = 0; maxabs = 0.0; bad_rows = []; done = 0
    while done < N0:
        n = min(BLK, N0 - done)
        A = np.frombuffer(fa.read(n * rowsz), dtype=da).reshape((n,) + sa[1:]); B = np.frombuffer(fb.read(n * rowsz), dtype=db).reshape((n,) + sb[1:])
        ia, ib = np.isnan(A), np.isnan(B); eq_nanpat += int((ia == ib).sum()); n_fin += int((~ia).sum())
        bits = (A.view(np.uint16) == B.view(np.uint16)); eq_bits += int(bits.sum())
        both = ~ia & ~ib
        if both.any():
            d = np.abs(A[both].astype(np.float32) - B[both].astype(np.float32)); maxabs = max(maxabs, float(d.max()))
        if not bits.all(): bad_rows.extend(int(x) + done for x in np.unique(np.nonzero(~bits)[0])[:50])
        done += n
    fa.close(); fb.close()
    za = np.load(BASE, allow_pickle=True); ts_a = za["ts"].astype(np.int64)
    ax = {"ts_prefix_bitwise_equal": bool(np.array_equal(ts_a, ts_b[:len(ts_a)])),
          "symbols_identical": [str(x) for x in za["symbols"]] == [str(x) for x in zb["symbols"]],
          "ch_identical": [str(x) for x in za["ch"]] == [str(x) for x in zb["ch"]],
          "rows_base": int(len(ts_a)), "rows_new": int(len(ts_b)), "rows_appended": int(len(ts_b) - len(ts_a)),
          "base_end_utc": time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(int(ts_a[-1]))), "new_end_utc": time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(int(ts_b[-1]))),
          "new_ts_step_300": bool(np.all(np.diff(ts_b) == 300))}
    r = {"base": BASE, "base_sha256": sha(BASE), "cells_compared": int(tot), "expected_cells_arithmetic": int(N0 * sa[1] * sa[2]),
         "nan_pattern_diff": int(tot - eq_nanpat), "bitwise_diff": int(tot - eq_bits), "n_finite_base": int(n_fin),
         "maxabs_diff_both_finite": maxabs, "first_bad_rows": bad_rows[:50], "axes": ax}
    r["PASS"] = bool(r["bitwise_diff"] == 0 and r["nan_pattern_diff"] == 0 and r["cells_compared"] == r["expected_cells_arithmetic"] and all(
        ax[k] for k in ("ts_prefix_bitwise_equal", "symbols_identical", "ch_identical", "new_ts_step_300")))
    rep["per_base"][os.path.basename(BASE)] = r
    print(json.dumps(r), flush=True)
rep["VERDICT"] = "PASS" if all(r["PASS"] for r in rep["per_base"].values()) else "FAIL"
rep["wall_s"] = round(time.time() - t0, 1); rep["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
json.dump(rep, open(RPT, "w"), indent=1)
print("AX03B_BW", rep["VERDICT"], flush=True)
sys.exit(0 if rep["VERDICT"] == "PASS" else 3)
