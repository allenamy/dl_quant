#!/usr/bin/env python3
"""s1_prod_betas_local.py — R10 A.4-5 (β 原始价 vs f16 裁剪) stage 1, LOCAL Mac, read-only, numpy only.

PRODUCTION beta device = beta_overlay_producer.compute (producer_copy/fea171, sha pinned below), called exactly as combo_stage.py
L379 does:  compute(rts, RD[:, :, 0], [str(x) for x in _symbols], list(_uni), A)
  rts, RD  = rolling.npz["ts"], rolling.npz["data"]   (feature_cache_identity.capture_producer_inputs; here: the 13:20Z COPY)
  _symbols = fea171/xfer_syms.npz["symbols"]          (capture_producer_inputs `axes`; here: a copy, sha pinned)
  channel 0 of data is "ret5" — asserted from xfer_syms["ch"] and feature_cache_identity.CHANNELS (not assumed)
  _uni     = the published target_live/<A>.json["universe"] (copies, sidecar sha verified)
Also (diagnostics only, never used to replace compute's output):
  * the cache 4h bars (same rule as compute) over the union window, all 829 columns, and an independent OLS replication that must
    equal compute's betas;
  * ret5 cells at the +-0.30 clip (float16(+-0.30) exactly) inside each anchor's 8,641-row window;
  * REVISION CHECK: for the anchors whose as-of-A rolling.npz was archived by combo_state_snapshot.sh (~/wide_shadow/state/snap/<A>,
    read-only, sha checked against the snapshot's SHA256SUMS), the window rows of the snapshot vs today's copy, cell by cell, and
    compute() on the snapshot vs compute() on today's copy.
Writes only <out>/work/S1_prod_local.npz and <out>/work/S1_prod_local.json.
usage: /usr/bin/python3 -B s1_prod_betas_local.py <out_root>
"""
import hashlib
import json
import os
import sys
import time

import numpy as np

T0 = time.time()
OUT = os.path.abspath(sys.argv[1])
IN = "/Users/haosiyu/cc_tmp/m3_impl_20260923/beta_parity/inputs"
PC = "/Users/haosiyu/cc_tmp/m3_impl_20260923/producer_copy/fea171"
SNAP = "/Users/haosiyu/wide_shadow/state/snap"                   # read-only
LIVE_AXES = {"xfer_syms_live": "/Users/haosiyu/wide_shadow/fea171/xfer_syms.npz",   # read-only (identity cross-check only)
             "xfer_ref_live": "/Users/haosiyu/wide_shadow/fea171/xfer_ref.npz",
             "config_live": "/Users/haosiyu/wide_shadow/shadow_bundle/config.json"}
PINS = {"rolling_copy": (IN + "/rolling_copy.npz", "73018d365cc00b362c78636156b0e059722f98d5cedf4348aebf2826960851e3"),
        "xfer_syms_copy": (IN + "/xfer_syms.npz", "d187042e60b480d3bb9e2d57757a1000da80428541011eeec67e330748ae1c92"),
        "beta_overlay_producer": (PC + "/beta_overlay_producer.py", "b77c180d69170988780566e19d0ee4a0f85af25a9b9e9be08b6e4a386095fb58"),
        "combo_stage": (PC + "/combo_stage.py", "41f9174d7d6400f5964e7cdf878efce58ef3965dd202b6a364f6e45c8d166d3c"),
        "feature_cache_identity": (PC + "/feature_cache_identity.py", "55bdef28def0e2a6faf1f28f6759cbcc48a4a947cf23214d05c2791bef9e4428")}
H4, ROW, NWIN = 14400, 300, 180
A_FIRST, A_LAST = 1789315200, 1789776000                           # 2026-09-13T16:00Z .. 2026-09-19T00:00Z
ANCHORS = list(range(A_FIRST, A_LAST + 1, H4))


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def utc(t):
    return time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(int(t)))


def log(*a):
    print("[%6.1fs]" % (time.time() - T0), *a, flush=True)


rec = {"device": "s1_prod_betas_local.py", "self_sha256": sha(os.path.abspath(__file__)), "argv": sys.argv,
       "python": sys.version, "numpy": np.__version__, "utc_start": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
       "inputs": {}, "checks": []}
FAILS = []


def check(name, ok, detail=None):
    rec["checks"].append({"check": name, "ok": bool(ok), "detail": detail})
    log("CHECK", name, "OK" if ok else "FAIL", json.dumps(detail, default=str)[:240] if detail is not None else "")
    if not ok:
        FAILS.append(name)


for k, (p, s) in PINS.items():
    got = sha(p)
    rec["inputs"][k] = {"path": p, "sha256": got}
    check("pin." + k, got == s, {"got": got[:16], "want": s[:16]})
for k, p in LIVE_AXES.items():
    rec["inputs"][k] = {"path": p, "sha256": sha(p), "mtime_utc": utc(os.path.getmtime(p))}
if FAILS:
    sys.exit("REFUSED: pins")

sys.path.insert(0, PC)
import beta_overlay_producer as B          # noqa: E402
import feature_cache_identity as FCI       # noqa: E402
check("module_file_is_pinned_copy", os.path.abspath(B.__file__) == PINS["beta_overlay_producer"][0], B.__file__)
rec["producer_params"] = {"VERSION": B.VERSION, "N_WIN": B.N_WIN, "N_MIN": B.N_MIN, "CLIP": [B.CLIP_LO, B.CLIP_HI], "FALLBACK": B.FALLBACK}

# ── load exactly as the producer / T8 do ──
z = np.load(PINS["rolling_copy"][0], allow_pickle=True)
log("rolling keys", z.files)
rts, D = z["ts"], z["data"]
ax = np.load(PINS["xfer_syms_copy"][0], allow_pickle=True)
log("xfer_syms keys", ax.files)
syms = [str(s) for s in ax["symbols"]]
ch = tuple(str(c) for c in ax["ch"])
check("axes.channels_eq_FCI.CHANNELS", ch == FCI.CHANNELS, ch)
check("axes.channel0_is_ret5", ch[0] == "ret5", ch[0])
check("data.shape", D.shape == (len(rts), len(syms), len(ch)), [list(D.shape), len(rts), len(syms), len(ch)])
check("data.dtype_float16", D.dtype == np.float16, str(D.dtype))
check("rts.int_contiguous", np.issubdtype(rts.dtype, np.integer) and bool(np.all(np.diff(rts.astype(np.int64)) == ROW)),
      {"dtype": str(rts.dtype), "first": utc(rts[0]), "last": utc(rts[-1]), "n": len(rts)})
# production identity of the ordered axis (capture_producer_inputs: names == xfer_ref symbols == cfg symbols_panel)
ref_syms = [str(s) for s in np.load(LIVE_AXES["xfer_ref_live"], allow_pickle=True)["symbols"]]
cfg_syms = list(json.load(open(LIVE_AXES["config_live"]))["symbols_panel"])
check("axes.copy_eq_live_xfer_syms", rec["inputs"]["xfer_syms_live"]["sha256"] == PINS["xfer_syms_copy"][1])
check("axes.symbols_eq_xfer_ref_eq_cfg_symbols_panel", syms == ref_syms == cfg_syms, [len(syms), len(ref_syms), len(cfg_syms)])
rts = rts.astype(np.int64)
ret5 = D[:, :, 0]                       # float16 view of channel 0 (compute converts the slice to float64)
ncol = len(syms)
col = {s: j for j, s in enumerate(syms)}
row_of = {int(t): i for i, t in enumerate(rts.tolist())}

# anchor coverage census (every published target_live anchor the cache axis contains)
tl_all = sorted(int(f[:-5]) for f in os.listdir("/Users/haosiyu/wide_shadow/state/target_live") if f.endswith(".json"))
need = NWIN * 48 + 1
full = [a for a in tl_all if a in row_of and row_of[a] - (need - 1) >= 0]
part = [a for a in tl_all if a in row_of and row_of[a] - (need - 1) < 0]
rec["coverage_census"] = {"cache_first_row_close": utc(rts[0]), "cache_last_row_close": utc(rts[-1]), "n_rows": len(rts),
                          "target_live_files": len(tl_all), "fully_covered_anchors_with_target_live": [utc(full[0]), utc(full[-1]), len(full)],
                          "partially_covered_anchors_with_target_live": [utc(part[0]), utc(part[-1]), len(part)] if part else None,
                          "partially_covered_with_ge120_possible_bars": int(sum(1 for a in part if sum(1 for k in range(NWIN) if a - (k + 1) * H4 >= int(rts[0])) >= 120)),
                          "comparison_anchors": [utc(A_FIRST), utc(A_LAST), len(ANCHORS)]}
check("comparison_anchors_all_fully_covered", all(a in full for a in ANCHORS), len(ANCHORS))


def bars(R16, ai):
    """cache 4h bars ending at rts[ai], rts[ai]-4h, ... (NWIN of them), the producer's rule, over all columns of R16 (float16 slice)."""
    lo = ai - (need - 1)
    R = np.asarray(R16[lo:ai + 1], dtype=np.float64)
    with np.errstate(invalid="ignore", divide="ignore"):
        L = np.log1p(R)
    fin = np.isfinite(L)
    m = R.shape[1]
    body_ok = fin[1:].reshape(NWIN, 48, m).all(axis=1)
    start_ok = fin[0:NWIN * 48:48]
    V = body_ok & start_ok
    R4 = np.where(V, np.where(fin[1:].reshape(NWIN, 48, m), L[1:].reshape(NWIN, 48, m), 0.0).sum(axis=1), np.nan)
    return R4, V


def ols(R4, V, jb):
    vb = V[:, jb]
    out = np.full(R4.shape[1], np.nan)
    n = (V & vb[:, None]).sum(0)
    for k in range(R4.shape[1]):
        m = V[:, k] & vb
        if m.sum() < B.N_MIN:
            continue
        x = R4[m, jb]; y = R4[m, k]
        dx = x - x.mean(); dy = y - y.mean()
        out[k] = float((dx * dy).sum()) / float((dx * dx).sum())
    return out, n


C16 = np.float16(0.3)
jb = col["BTCUSDT"]
tl = {}
per = {}
names_union = []
for A in ANCHORS:
    p = f"{IN}/target_live/{A}.json"
    raw = open(p, "rb").read()
    side = open(p + ".sha256").read().split()[0]
    s = hashlib.sha256(raw).hexdigest()
    rec["inputs"][f"target_live_{A}"] = {"path": p, "source": f"/Users/haosiyu/wide_shadow/state/target_live/{A}.json", "sha256": s}
    if s != side:
        check(f"target_live.{A}.sidecar", False, {"got": s[:16], "sidecar": side[:16]})
    doc = json.loads(raw)
    if not (doc.get("anchor_ts") == A and isinstance(doc.get("universe"), list) and isinstance(doc.get("weights"), dict)):
        check(f"target_live.{A}.keys", False, sorted(doc))
    uni = list(doc["universe"]); W = {str(k): float(v) for k, v in doc["weights"].items()}
    t1 = time.time()
    f = B.compute(rts, ret5, syms, uni, A)          # ← THE production device, as combo_stage L379 calls it
    el = time.time() - t1
    want = list(f["betas"])
    ai = row_of[A]
    R4, V = bars(ret5, ai)
    rep, nrep = ols(R4, V, jb)
    diffs = []
    for n in want:
        if n not in col:
            continue
        k = col[n]
        if n == "BTCUSDT":
            continue
        b = f["betas"][n]
        if np.isfinite(rep[k]):
            diffs.append(abs(min(max(rep[k], -1.0), 4.0) - b))
            if int(nrep[k]) != f["n_obs"][n]:
                diffs.append(np.inf)
        else:
            if not (b == 1.0 and f["n_obs"][n] == int(nrep[k])):
                diffs.append(np.inf)
    lo = ai - (need - 1)
    W16 = ret5[lo:ai + 1]
    clip_mask = (W16 == C16) | (W16 == -C16)
    over = np.abs(W16.astype(np.float32)) > np.float32(C16)
    per[A] = {"field": f, "elapsed_s": round(el, 3), "rep_max_abs": float(max(diffs) if diffs else 0.0),
              "n_clip_cells_all_cols": int(clip_mask.sum()), "n_over_clip": int(over.sum()),
              "clip_cells": [(int(rts[lo + r]), syms[c], float(W16[r, c])) for r, c in zip(*np.nonzero(clip_mask))],
              "nan_rows_per_col": np.isnan(W16.astype(np.float32)).sum(0).astype(np.int32),
              "own_valid_bars": V.sum(0).astype(np.int32)}
    tl[A] = {"universe": uni, "weights": W, "gross_norm": doc.get("gross_norm"), "n_names": doc.get("n_names"),
             "has_beta_overlay_field": "beta_overlay" in doc, "keys": sorted(doc)}
    for n in want:
        if n not in names_union:
            names_union.append(n)
    log(utc(A), "n_names", f["n_names"], "est", f["n_estimated"], "fb", f["n_fallback"], "nocol", f["n_no_cache_column"],
        "rep_max", per[A]["rep_max_abs"], "clip_cells", per[A]["n_clip_cells_all_cols"], "t", per[A]["elapsed_s"])
check("replication_equals_compute_every_anchor", max(per[A]["rep_max_abs"] for A in ANCHORS) < 1e-12,
      max(per[A]["rep_max_abs"] for A in ANCHORS))
check("no_value_beyond_clip", all(per[A]["n_over_clip"] == 0 for A in ANCHORS))
check("target_live_has_no_beta_overlay_field_in_window", not any(tl[A]["has_beta_overlay_field"] for A in ANCHORS))

# union-window cache bars for all 829 columns (for the bar-by-bar comparison with the certified table)
Tb = np.arange(A_FIRST - (NWIN - 1) * H4, A_LAST + 1, H4, dtype=np.int64)
R4u = np.full((len(Tb), ncol), np.nan); Vu = np.zeros((len(Tb), ncol), bool)
for i, T in enumerate(Tb.tolist()):
    a = row_of[T]; s0 = a - 48
    R = np.asarray(ret5[s0:a + 1], np.float64)
    with np.errstate(invalid="ignore", divide="ignore"):
        L = np.log1p(R)
    fin = np.isfinite(L)
    v = fin.all(0)
    Vu[i] = v
    R4u[i] = np.where(v, np.where(fin[1:], L[1:], 0.0).sum(0), np.nan)
# consistency: last anchor's window bars from the per-anchor function equal the union bars
R4l, Vl = bars(ret5, row_of[A_LAST])
check("union_bars_eq_anchor_bars", np.array_equal(Vl, Vu[-NWIN:]) and np.array_equal(np.nan_to_num(R4l, nan=9.0), np.nan_to_num(R4u[-NWIN:], nan=9.0)))

# union-window clip cells (rows closing in [A_FIRST-180*4h, A_LAST])
lo_u, hi_u = row_of[A_FIRST - NWIN * H4], row_of[A_LAST]
Wu = ret5[lo_u:hi_u + 1]
cm = (Wu == C16) | (Wu == -C16)
clip_rows, clip_cols = np.nonzero(cm)
clip_ts = rts[lo_u + clip_rows]

# ── REVISION CHECK against archived as-of-A snapshots ──
rev = {}
for A in ANCHORS:
    d = f"{SNAP}/{A}"
    if not os.path.isfile(d + "/rolling.npz"):
        continue
    sums = {}
    for line in open(d + "/SHA256SUMS"):
        h, fn = line.split()
        sums[fn] = h
    got = sha(d + "/rolling.npz")
    ok = got == sums.get("rolling.npz")
    rec["inputs"][f"snap_rolling_{A}"] = {"path": d + "/rolling.npz", "sha256": got, "sha_matches_SHA256SUMS": ok}
    if not ok:
        check(f"snap.{A}.sha", False)
        continue
    zs = np.load(d + "/rolling.npz", allow_pickle=True)
    ts_s, Ds = zs["ts"].astype(np.int64), zs["data"]
    if not (ts_s[-1] == A and Ds.shape[1] == ncol and Ds.dtype == np.float16):
        check(f"snap.{A}.axis", False, {"last": utc(ts_s[-1]), "shape": list(Ds.shape), "dtype": str(Ds.dtype)})
        continue
    ai_s = int(np.nonzero(ts_s == A)[0][0]); lo_s = ai_s - (need - 1)
    a_t = row_of[A]; lo_t = a_t - (need - 1)
    check(f"snap.{A}.window_ts_equal", np.array_equal(ts_s[lo_s:ai_s + 1], rts[lo_t:a_t + 1]))
    S = Ds[lo_s:ai_s + 1, :, 0]; Tq = ret5[lo_t:a_t + 1]
    sn, tn = np.isnan(S.astype(np.float32)), np.isnan(Tq.astype(np.float32))
    same = (S.view(np.uint16) == Tq.view(np.uint16)) | (sn & tn)
    fs = B.compute(ts_s, Ds[:, :, 0], syms, tl[A]["universe"], A)
    ft = per[A]["field"]
    db = {n: fs["betas"][n] - ft["betas"][n] for n in ft["betas"]}
    dn = {n: fs["n_obs"][n] - ft["n_obs"][n] for n in ft["n_obs"]}
    uni_cols = [col[n] for n in tl[A]["universe"] if n in col] + [jb]
    rev[A] = {"cells_differ_all_cols": int((~same).sum()),
              "nan_to_value": int((sn & ~tn).sum()), "value_to_nan": int((~sn & tn).sum()),
              "value_changed": int((~sn & ~tn & ~same).sum()),
              "cells_differ_universe_cols": int((~same[:, uni_cols]).sum()),
              "rows_differ_last_row_close": (utc(ts_s[lo_s + int(np.nonzero((~same).any(1))[0].max())]) if (~same).any() else None),
              "rows_differ_first_row_close": (utc(ts_s[lo_s + int(np.nonzero((~same).any(1))[0].min())]) if (~same).any() else None),
              "names_beta_differs": {n: [round(fs["betas"][n], 12), round(ft["betas"][n], 12)] for n in db if db[n] != 0.0},
              "max_abs_dbeta": float(max(abs(v) for v in db.values())), "n_obs_differs": {n: dn[n] for n in dn if dn[n] != 0},
              "field_byte_identical": json.dumps(fs, sort_keys=True) == json.dumps(ft, sort_keys=True)}
    log("snap", utc(A), {k: v for k, v in rev[A].items() if k not in ("names_beta_differs", "n_obs_differs")},
        "n_names_beta_differs", len(rev[A]["names_beta_differs"]))
    del zs, Ds, S
rec["revision_check"] = {utc(A): v for A, v in rev.items()}

# ── write ──
UN = names_union
nA, nN = len(ANCHORS), len(UN)
BP = np.full((nA, nN), np.nan); NP = np.full((nA, nN), -1, np.int32); INU = np.zeros((nA, nN), bool); WT = np.zeros((nA, nN))
HASCOL = np.array([n in col for n in UN]); CL_CNT = np.zeros((nA, nN), np.int32); NANR = np.full((nA, nN), -1, np.int32)
OWNV = np.full((nA, nN), -1, np.int32)
wt_missing = {}
for a_i, A in enumerate(ANCHORS):
    f = per[A]["field"]
    for n_i, n in enumerate(UN):
        if n in f["betas"]:
            BP[a_i, n_i] = f["betas"][n]; NP[a_i, n_i] = f["n_obs"][n]; INU[a_i, n_i] = True
            if n in col:
                NANR[a_i, n_i] = per[A]["nan_rows_per_col"][col[n]]; OWNV[a_i, n_i] = per[A]["own_valid_bars"][col[n]]
        WT[a_i, n_i] = tl[A]["weights"].get(n, 0.0)
    miss = [n for n in tl[A]["weights"] if n not in f["betas"]]
    if miss:
        wt_missing[utc(A)] = miss
    cc = {}
    for (t, s, v) in per[A]["clip_cells"]:
        cc[s] = cc.get(s, 0) + 1
    for n_i, n in enumerate(UN):
        CL_CNT[a_i, n_i] = cc.get(n, 0)
check("every_weight_name_has_a_production_beta", not wt_missing, wt_missing)
rec["per_anchor"] = {utc(A): {"n_names": per[A]["field"]["n_names"], "n_estimated": per[A]["field"]["n_estimated"],
                              "n_fallback": per[A]["field"]["n_fallback"], "n_no_cache_column": per[A]["field"]["n_no_cache_column"],
                              "elapsed_s": per[A]["elapsed_s"], "n_clip_cells_all_cols": per[A]["n_clip_cells_all_cols"],
                              "n_clip_cells_universe": int(sum(1 for (t, s, v) in per[A]["clip_cells"] if s in set(tl[A]["universe"]) | {"BTCUSDT"})),
                              "n_weights": len(tl[A]["weights"]), "gross_norm_file": tl[A]["gross_norm"],
                              "first_bar_end": utc(per[A]["field"]["first_bar_end_ts"])} for A in ANCHORS}
os.makedirs(OUT + "/work", exist_ok=True)
np.savez_compressed(OUT + "/work/S1_prod_local.npz", anchors=np.array(ANCHORS, np.int64), names=np.array(UN), beta_prod=BP, nobs_prod=NP,
                    in_field=INU, weight=WT, has_cache_col=HASCOL, clip_cells_in_window=CL_CNT, nan_rows_in_window=NANR,
                    own_valid_bars=OWNV, cache_syms=np.array(syms), Tb=Tb, R4_cache=R4u, V_cache=Vu,
                    clip_ts=clip_ts.astype(np.int64), clip_col=clip_cols.astype(np.int64),
                    clip_val=Wu[clip_rows, clip_cols].astype(np.float32),
                    universe_json=np.array(json.dumps({str(A): tl[A]["universe"] for A in ANCHORS})),
                    weights_json=np.array(json.dumps({str(A): tl[A]["weights"] for A in ANCHORS})))
rec["outputs"] = {"npz": OUT + "/work/S1_prod_local.npz", "npz_sha256": sha(OUT + "/work/S1_prod_local.npz")}
rec["failed"] = FAILS
rec["runtime_s"] = round(time.time() - T0, 1)
json.dump(rec, open(OUT + "/work/S1_prod_local.json", "w"), indent=1, default=str)
print(("S1 ALL CHECKS OK" if not FAILS else f"S1 FAILURES {FAILS}"), "npz_sha256=" + rec["outputs"]["npz_sha256"], flush=True)
sys.exit(0 if not FAILS else 1)
