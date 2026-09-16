#!/usr/bin/env python3
"""fx_uni03_sep_mask.py — FX-DATA UNI-03 (pod2, CPU, read-only on every input). Committed before it is run.

UNI-03 (AUDIT_DATA bb8a2806, P3): `umask_UPIT_CRYPTO.npz` ends 2026-08-31 00Z, so every x0910 September reading carries the last
August row forward (declared in T2 and T5c). A September listing, delisting or monthly refresh is not reflected, and the size of
that approximation was never measured. The audit's action is "build a September mask row with the same monthly rule when September
is rolled". This device builds it and measures the difference. It writes NEW files beside the old ones and edits nothing.

The monthly rule, from `build_umask.py` (research copy `retrain_2026-09/health_check_2026-09-05/build_umask.py`, sha 746700fd):
at the FIRST panel anchor of each calendar month, rank symbols by trailing-30-day quote volume (sum of expm1(log_qv) over the 8640
5m bars strictly before the anchor) among symbols listed >= 30 days with positive volume, take the top 449, hold for the month.
Then `build_crypto_mask.py` intersects it with underlyingType in ("COIN", "INDEX"), keeping symbols absent from today's exchangeInfo.

No new cache lineage is needed: `dlnative_5m_wide829_f16_ext.npz` — the cache the committed mask was built from — ends exactly at
2026-09-01T00:00Z, which IS the first September anchor, and the 30-day window is the 8640 bars strictly before it. The September row
is therefore the same rule on the same cache, one month further on, not an extrapolation.

Boundary, and runs 12/13 got it wrong. The x0910 panel axis extends past the committed mask by 60 anchors, but five of them
(2026-08-31 04:00Z .. 20:00Z) are still AUGUST anchors, and the monthly rule assigns a row by calendar month, so they must keep
the August row. Runs 12 and 13 wrote the September row over those five. Rows are now assigned by the anchor's calendar month and
an assertion covers the August tail; the true September anchor count is 55, not 60.

  A  positive control: rebuild EVERY committed monthly row from that cache and require bitwise equality with the stored
     `umask_UPIT.npz`, and with `umask_UPIT_CRYPTO.npz` after the class filter. If either fails, no September row is written.
  B  the September row at 2026-09-01T00:00Z under the same rule and the same class vector.
  C  the difference against the carried-forward August row: names added, names dropped, and how many September anchors of the
     x0910 panel axis are affected.
  D  the honest gap: any September entrant whose venue class is absent from the 2026-09-08 exchangeInfo snapshot falls into
     build_crypto_mask.py's "unknown => kept" branch and is named, not silently kept.

Usage: python3 fx_uni03_sep_mask.py <out_dir> <out_receipt.json>
Exit 0 only if the positive control reproduced bitwise.
"""
import os, sys, json, time, zipfile
import numpy as np

ENV_WHITELIST = {"PATH", "HOME", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "PYTHONPATH"}
EXTRA = sorted(k for k in os.environ if k not in ENV_WHITELIST and k not in ("PWD", "SHLVL", "_", "OLDPWD", "LC_CTYPE"))
assert EXTRA == [], ("ENV WHITELIST VIOLATION", EXTRA)
os.nice(19)
OUT_DIR, OUT = sys.argv[1], sys.argv[2]
sys.path.insert(0, os.environ["PYTHONPATH"].split(":")[0])
import tradability as T

W = "/workspace"
CACHE = f"{W}/data/dlnative_5m_wide829_f16_ext.npz"
PANEL = f"{W}/data/wide_panel_4h_v2ext.npz"
PANEL_X = f"{W}/uplift_2026-09-11/r6/out/wide_panel_4h_v2ext_x0910.npz"
M_UPIT = f"{W}/review_scratch/health_check/masks/umask_UPIT.npz"
M_CRYPTO = f"{W}/review_scratch/health_check/masks/umask_UPIT_CRYPTO.npz"
VCLASS = f"{W}/aud_data_2026-09-13/devices/venue_class_20260908.json"
BARS30 = 30 * 288; TOPN = 449
T0 = time.time()
def utc(t): return time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(int(t)))
def log(*a): print("[%6.0fs]" % (time.time() - T0), *a, flush=True)

FAILS = []; CHECKS = []
def check(name, ok, detail=None):
    CHECKS.append({"check": name, "ok": bool(ok), **({"detail": detail} if detail is not None else {})})
    if not ok: FAILS.append(name)
    return ok

rec = {"device": "fx_uni03_sep_mask.py", "self_sha256": T.guarded_sha256(os.path.abspath(__file__)),
       "module_sha256": T.guarded_sha256(os.path.join(os.environ["PYTHONPATH"].split(":")[0], "tradability.py")),
       "numpy": np.__version__, "argv": sys.argv, "env": {k: os.environ[k] for k in sorted(os.environ)},
       "inputs": {p: T.guarded_sha256(p) for p in (CACHE, PANEL, PANEL_X, M_UPIT, M_CRYPTO, VCLASS)},
       "rule": "build_umask.py U-PIT: first panel anchor of each month, top %d by sum(expm1(log_qv)) over the %d bars strictly "
               "before it, among listed >= 30 days with positive volume; held for the month" % (TOPN, BARS30),
       "utc_start": utc(time.time())}

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

Z = np.load(CACHE, allow_pickle=True); CTS = Z["ts"].astype(np.int64); CSYM = [str(s) for s in Z["symbols"]]
CH = [str(c) for c in Z["ch"]]; iq = CH.index("log_qv"); ir = CH.index("ret5")
P = np.load(PANEL, allow_pickle=True); PTS = P["ts"].astype(np.int64); PSYM = [str(s) for s in P["symbols"]]
assert PSYM == CSYM, "panel/cache symbol order differs"
PX = np.load(PANEL_X, allow_pickle=True); PTSX = PX["ts"].astype(np.int64)
assert [str(s) for s in PX["symbols"]] == PSYM and np.array_equal(PTSX[:len(PTS)], PTS)
NW = len(PSYM)
DA, shp = stream_channels(CACHE, sorted({ir, iq}))
cix = {c: k for k, c in enumerate(sorted({ir, iq}))}
ret5 = DA[:, :, cix[ir]].astype(np.float32); lq = DA[:, :, cix[iq]].astype(np.float32); del DA
fin = np.isfinite(ret5); has = fin.any(0); first_idx = np.argmax(fin, 0)
_fi_lq0 = np.argmax(np.isfinite(lq), 0)
first_ts = np.where(has, np.where(_fi_lq0 <= 2, CTS[0], CTS[np.clip(_fi_lq0, 0, len(CTS) - 1)]), 2**62)
del ret5, fin, first_idx
qv5 = np.expm1(np.clip(np.nan_to_num(lq, nan=0.0), 0, 30)).astype(np.float64); del lq
cs = np.zeros((len(CTS) + 1, NW), np.float64); np.cumsum(qv5, axis=0, out=cs[1:]); del qv5
log("cumsum done, cache rows", len(CTS), "last", utc(CTS[-1]))
pos = {int(t): k for k, t in enumerate(CTS)}

def month_row(anchor_ts):
    """the U-PIT allowed set at one monthly anchor, build_umask.py L33-45 semantics"""
    k = pos[int(anchor_ts)]; lo = max(0, k - BARS30)
    vol30 = cs[k] - cs[lo]
    age = (int(anchor_ts) - first_ts) / 86400.0
    elig = has & (age >= 30) & (vol30 > 0)
    order = np.argsort(-vol30); order = order[elig[order]]; top = order[:TOPN]
    m = np.zeros(NW, bool); m[top] = True
    return m, {"anchor": utc(anchor_ts), "bars_used": int(k - lo), "n_listed": int((first_ts <= int(anchor_ts)).sum()),
               "n_elig": int(elig.sum()), "n_top": int(len(top)),
               "vol30_449th_usd": (float(vol30[top[-1]]) if len(top) else None)}

# ---------------- A. positive control on every committed monthly row ----------------
mstart = {}
for j, t in enumerate(PTS):
    tm = time.gmtime(int(t)); key = (tm.tm_year, tm.tm_mon)
    if key not in mstart: mstart[key] = j
keys = sorted(mstart)
UPIT = np.zeros((len(PTS), NW), bool); rows = []
for n, key in enumerate(keys):
    j0 = mstart[key]; j1 = mstart[keys[n + 1]] if n + 1 < len(keys) else len(PTS)
    m, info = month_row(PTS[j0]); UPIT[j0:j1] = m
    info["month"] = "%d-%02d" % key; info["n_anchors"] = int(j1 - j0); rows.append(info)
SU = np.load(M_UPIT, allow_pickle=True); SC = np.load(M_CRYPTO, allow_pickle=True)
assert np.array_equal(SU["ts"].astype(np.int64), PTS) and np.array_equal(SC["ts"].astype(np.int64), PTS)
check("A.upit_rebuilt_bitwise", bool(np.array_equal(UPIT, np.asarray(SU["mask"]))),
      {"cells": int(UPIT.size), "differing": int((UPIT != np.asarray(SU["mask"])).sum())})
CLS = json.load(open(VCLASS))
coin = np.array([(CLS[s]["underlyingType"] in ("COIN", "INDEX")) if s in CLS else True for s in PSYM])
unknown = [s for s in PSYM if s not in CLS]
CRY = UPIT & coin[None, :]
check("A.crypto_rebuilt_bitwise", bool(np.array_equal(CRY, np.asarray(SC["mask"]))),
      {"cells": int(CRY.size), "differing": int((CRY != np.asarray(SC["mask"])).sum()),
       "n_unknown_class": len(unknown)})
rec["A_monthly_rows"] = {"n_months": len(keys), "first": rows[0], "last": rows[-1], "n_unknown_class": len(unknown)}
log("A control upit/crypto", CHECKS[-2]["ok"], CHECKS[-1]["ok"])
if FAILS:
    rec["checks"] = CHECKS; rec["n_failed"] = len(FAILS); rec["stopped_before_september_row"] = True
    json.dump(rec, open(OUT, "w"), indent=1)
    print("FX_UNI03_STOPPED_POSITIVE_CONTROL", json.dumps(FAILS), flush=True); sys.exit(1)

# ---------------- B. the September row ----------------
SEP_ANCHOR = int(PTSX[np.searchsorted(PTSX, 1788220800)])          # 2026-09-01T00:00Z on the x0910 panel axis
assert SEP_ANCHOR == 1788220800, utc(SEP_ANCHOR)
check("B.september_anchor_is_in_the_cache", int(SEP_ANCHOR) in pos,
      {"anchor": utc(SEP_ANCHOR), "cache_last_bar": utc(CTS[-1])})
sep, sep_info = month_row(SEP_ANCHOR)
sep_c = sep & coin
aug_j = mstart[(2026, 8)]
aug = UPIT[aug_j].copy(); aug_c = CRY[aug_j].copy()
rec["B_september_row"] = {**sep_info, "n_allowed_upit": int(sep.sum()), "n_allowed_crypto": int(sep_c.sum()),
                          "august_row_anchor": utc(PTS[aug_j]), "august_n_allowed_upit": int(aug.sum()),
                          "august_n_allowed_crypto": int(aug_c.sum())}
log("B", json.dumps(rec["B_september_row"]))

# ---------------- C. what the carried-forward row gets wrong ----------------
add = [PSYM[j] for j in np.where(sep_c & ~aug_c)[0]]
drop = [PSYM[j] for j in np.where(aug_c & ~sep_c)[0]]
# the monthly rule assigns a row by CALENDAR MONTH of the anchor, so the x0910 tail is not all September:
# 2026-08-31 04:00Z..20:00Z are August anchors and must keep the August row. Runs 12/13 wrote the September row over them.
is_sep = np.array([(time.gmtime(int(t)).tm_year, time.gmtime(int(t)).tm_mon) == (2026, 9) for t in PTSX])
tail = np.zeros(len(PTSX), bool); tail[len(PTS):] = True
aug_tail = tail & ~is_sep
sep_rows = int(is_sep.sum())
rec["C_difference"] = {"september_anchors_on_x0910_axis": sep_rows,
                       "first_september_anchor": utc(PTSX[int(np.argmax(is_sep))]) if sep_rows else None,
                       "x0910_tail_anchors_beyond_the_committed_mask": int(tail.sum()),
                       "of_which_still_august": int(aug_tail.sum()),
                       "still_august_anchors": [utc(t) for t in PTSX[aug_tail]],
                       "last_x0910_anchor": utc(PTSX[-1]),
                       "added_by_the_september_rule": sorted(add), "n_added": len(add),
                       "dropped_by_the_september_rule": sorted(drop), "n_dropped": len(drop),
                       "cells_changed_per_september_anchor": len(add) + len(drop),
                       "share_of_the_allowed_set": round((len(add) + len(drop)) / max(int(aug_c.sum()), 1), 4),
                       "upit_only_added": sorted(PSYM[j] for j in np.where(sep & ~aug)[0]),
                       "upit_only_dropped": sorted(PSYM[j] for j in np.where(aug & ~sep)[0])}
# month-over-month churn of the allowed set, so the September difference can be read against the normal rate
churn = []
for n in range(1, len(keys)):
    a = CRY[mstart[keys[n - 1]]]; b = CRY[mstart[keys[n]]]
    churn.append({"month": "%d-%02d" % keys[n], "n_allowed": int(b.sum()), "added": int((b & ~a).sum()), "dropped": int((a & ~b).sum())})
ch12 = churn[-12:]
rec["C_monthly_churn_for_scale"] = {
    "definition": "added/dropped in the CRYPTO allowed set at each month's own first anchor, versus the previous month's row",
    "last_12_months": ch12,
    "median_added_last_12": float(np.median([c["added"] for c in ch12])),
    "median_dropped_last_12": float(np.median([c["dropped"] for c in ch12])),
    "median_added_all": float(np.median([c["added"] for c in churn])),
    "median_dropped_all": float(np.median([c["dropped"] for c in churn])),
    "all_months": churn}
rec["D_unknown_class_among_entrants"] = sorted(s for s in add if s not in CLS)
rec["D_note"] = ("build_crypto_mask.py keeps a symbol absent from the exchangeInfo snapshot ('unknown => kept'). Entrants in that "
                 "state are named here rather than silently kept; the snapshot is venue_class_20260908.json.")
log("C", len(add), "added,", len(drop), "dropped;", sep_rows, "September anchors")

# ---------------- write the x0910-axis masks ----------------
def det_npz(path, arrays):
    tmp = path + ".tmp"
    with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for k in sorted(arrays):
            zi = zipfile.ZipInfo(k + ".npy", date_time=(1980, 1, 1, 0, 0, 0)); zi.compress_type = zipfile.ZIP_DEFLATED
            a = np.asarray(arrays[k]); a = a if a.ndim == 0 else np.ascontiguousarray(a)
            with zf.open(zi, "w", force_zip64=True) as fh: np.lib.format.write_array(fh, a, allow_pickle=False)
    os.replace(tmp, path)
os.makedirs(OUT_DIR, exist_ok=True)
nX = len(PTSX)
MX_U = np.zeros((nX, NW), bool); MX_U[:len(PTS)] = UPIT
MX_U[aug_tail] = UPIT[aug_j]; MX_U[is_sep] = sep                 # by calendar month, not by "past the old axis"
MX_C = np.zeros((nX, NW), bool); MX_C[:len(PTS)] = CRY
MX_C[aug_tail] = CRY[aug_j]; MX_C[is_sep] = sep_c
check("W.august_tail_anchors_keep_the_august_row",
      bool(np.array_equal(MX_C[aug_tail], np.tile(CRY[aug_j], (int(aug_tail.sum()), 1)))),
      {"anchors": int(aug_tail.sum())})
check("W.august_prefix_unchanged", bool(np.array_equal(MX_C[:len(PTS)], np.asarray(SC["mask"]))), {"rows": int(len(PTS))})
outs = {}
for nm, arr in (("umask_UPIT_x0910_sep", MX_U), ("umask_UPIT_CRYPTO_x0910_sep", MX_C)):
    p = os.path.join(OUT_DIR, nm + ".npz")
    det_npz(p, {"ts": PTSX, "symbols": np.array(PSYM), "mask": arr,
                "september_row_anchor": np.array(SEP_ANCHOR, np.int64),
                "built_from": np.array("fx_uni03_sep_mask.py; prefix identical to the committed mask, September rows = the "
                                       "2026-09-01T00:00Z U-PIT row under build_umask.py's rule")})
    outs[nm] = {"path": p, "sha256": T.guarded_sha256(p), "bytes": os.path.getsize(p)}
rec["outputs"] = outs
rec["checks"] = CHECKS; rec["n_checks"] = len(CHECKS); rec["n_failed"] = len(FAILS); rec["failed"] = FAILS
rec["runtime_s"] = round(time.time() - T0, 1); rec["utc_end"] = utc(time.time())
json.dump(rec, open(OUT, "w"), indent=1)
print("FX_UNI03_DONE", json.dumps({"failed": len(FAILS), "added": len(add), "dropped": len(drop),
                                   "median_added_last_12": rec["C_monthly_churn_for_scale"]["median_added_last_12"],
                                   "median_dropped_last_12": rec["C_monthly_churn_for_scale"]["median_dropped_last_12"],
                                   "september_anchors": sep_rows,
                                   "crypto_sha256": outs["umask_UPIT_CRYPTO_x0910_sep"]["sha256"]}), flush=True)
sys.exit(1 if FAILS else 0)
