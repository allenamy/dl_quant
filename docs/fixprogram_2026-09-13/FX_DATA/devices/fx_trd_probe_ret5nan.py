#!/usr/bin/env python3
"""fx_trd_probe_ret5nan.py — FX-DATA TRD-01 descriptive probe (pod2, CPU, read-only). Committed before it is run.

fx_trd_verify.py V2 counted 840 cells that the SPEC calls TRADED and the audit device (which gates on isfinite(ret5)) does not,
and 1 cell that the SPEC calls UNTRADED and the audit does not. Its example list was truncated at 50 and every example sat on the
first bar of the cache, but 840 > 829 symbols, so not all of them can be first bars. This probe reports the exact distribution:
by bar close time, by symbol, and split into "first bar of the cache" / "first bar of that symbol's data" / "first bar after a
NODATA gap" / "none of these". No decision reads this; it exists so the fact table row is exact.

Usage: python3 fx_trd_probe_ret5nan.py <out_receipt.json>
"""
import os, sys, json, time, zipfile
import numpy as np

ENV_WHITELIST = {"PATH", "HOME", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "PYTHONPATH"}
EXTRA = sorted(k for k in os.environ if k not in ENV_WHITELIST and k not in ("PWD", "SHLVL", "_", "OLDPWD", "LC_CTYPE"))
assert EXTRA == [], ("ENV WHITELIST VIOLATION", EXTRA)
os.nice(19)
OUT = sys.argv[1]
sys.path.insert(0, os.environ["PYTHONPATH"].split(":")[0])
import tradability as T

CACHE = "/workspace/data/dlnative_5m_wide829_f16_holefix2.npz"
T0 = time.time()
def utc(t): return time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(int(t)))
def log(*a): print("[%6.0fs]" % (time.time() - T0), *a, flush=True)

rec = {"device": "fx_trd_probe_ret5nan.py", "self_sha256": T.guarded_sha256(os.path.abspath(__file__)),
       "module_sha256": T.guarded_sha256(os.path.join(os.environ["PYTHONPATH"].split(":")[0], "tradability.py")),
       "numpy": np.__version__, "argv": sys.argv, "env": {k: os.environ[k] for k in sorted(os.environ)},
       "inputs": {CACHE: T.guarded_sha256(CACHE)}, "utc_start": utc(time.time())}

def stream_channels(path, chans, block=20000):
    zf = zipfile.ZipFile(path)
    with zf.open("data.npy") as fh:
        ver = np.lib.format.read_magic(fh)
        shape, fort, dt = (np.lib.format.read_array_header_1_0(fh) if ver == (1, 0) else np.lib.format.read_array_header_2_0(fh))
        assert not fort and len(shape) == 3
        rowb = int(np.prod(shape[1:])) * dt.itemsize
        out = np.empty((shape[0], shape[1], len(chans)), dt); r = 0
        while r < shape[0]:
            k = min(block, shape[0] - r); buf = fh.read(k * rowb); assert len(buf) == k * rowb
            out[r:r + k] = np.frombuffer(buf, dtype=dt).reshape((k,) + tuple(shape[1:]))[:, :, chans]; r += k
    return out, shape

Z = np.load(CACHE, allow_pickle=True); CTS = Z["ts"].astype(np.int64); syms = [str(s) for s in Z["symbols"]]
D, shp = stream_channels(CACHE, [0, 4]); R0 = D[:, :, 0]; C4 = D[:, :, 1]
S = T.bar_states(C4)
finR = np.isfinite(R0)
diff = (S != T.NODATA) & ~finR                 # a bar with a state under the SPEC but no finite return
r_, c_ = np.where(diff)
log("cells", len(r_))
have = S != T.NODATA
first_row_of_sym = np.where(have.any(0), np.argmax(have, 0), -1)
prev_nodata = np.zeros_like(have); prev_nodata[1:] = ~have[:-1]; prev_nodata[0] = True
cls = {"first_bar_of_cache": 0, "first_bar_of_symbol_not_cache": 0, "first_bar_after_nodata_gap": 0, "none_of_these": 0}
rows_by_ts = {}
per_sym = {}
detail = []
for i in range(len(r_)):
    r, c = int(r_[i]), int(c_[i])
    k = ("first_bar_of_cache" if r == 0 else
         "first_bar_of_symbol_not_cache" if r == first_row_of_sym[c] else
         "first_bar_after_nodata_gap" if prev_nodata[r, c] else "none_of_these")
    cls[k] += 1
    rows_by_ts[utc(CTS[r])] = rows_by_ts.get(utc(CTS[r]), 0) + 1
    per_sym[syms[c]] = per_sym.get(syms[c], 0) + 1
    if k == "none_of_these" or r != 0:
        detail.append({"symbol": syms[c], "ts": utc(CTS[r]), "class": k, "state": int(S[r, c]), "log_cnt": float(C4[r, c])})
rec["cells_state_without_finite_ret5"] = {
    "total": int(len(r_)), "TRADED": int((S[r_, c_] == T.TRADED).sum()), "UNTRADED": int((S[r_, c_] == T.UNTRADED).sum()),
    "classes": cls, "by_bar_close": dict(sorted(rows_by_ts.items(), key=lambda kv: -kv[1])[:20]),
    "distinct_symbols": len(per_sym), "cells_not_on_the_first_bar_of_the_cache": detail[:200]}
rec["runtime_s"] = round(time.time() - T0, 1); rec["utc_end"] = utc(time.time())
json.dump(rec, open(OUT, "w"), indent=1)
print("FX_TRD_PROBE_DONE", json.dumps(rec["cells_state_without_finite_ret5"]["classes"]),
      json.dumps({"total": int(len(r_)), "distinct_symbols": len(per_sym)}), flush=True)
