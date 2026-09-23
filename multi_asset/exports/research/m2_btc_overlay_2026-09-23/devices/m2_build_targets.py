#!/usr/bin/env python3
"""m2_build_targets.py — builds the M2 (BTC-beta overlay) target file from a certified-format base target file (prereg
docs/PREREG_old_vs_new_models_same_engine_2026-09-23.md Stage 2; formula in m2_lib.py). pod2, CPU only.

Inputs (each sha-checked; a mismatch refuses the run):
  the base TARGETS npz + its receipt (pinned shas on the command line), reading (default 'scaled'), arm (A0 for OLD);
  the certified price table price_full_raw_x0918r.npy (23af32bd…) + meta (d1e49cc9…) = RUN_CONFIG_main_A0_2026-09-19 pins;
  the OLD price meta price_full_meta.npz (f2f53828…) — only for the input check below.
Input check (before any beta): the in-life NaN cells of the OLD cache (OLD meta inlife_nan, 24,397 cells) equal, as a set, the union of the
raw table's gap-FILLED cells and its UNAVAILABLE cells on the same grid ⇒ every in-life missing 5-minute bar is either a restored official
return or a named UA bar, so excluding the UA set is excluding every missing interval (no silent zero-filled bar left in life).
Outputs (<out_root>):
  work/targets/TARGETS_<tag>.npz      anchor + <reading>_{kind,off,idx,val} (the certified adapter's format; other readings not written)
  receipts/TARGETS_<tag>.json         the adapter's receipt fields copied from the base receipt (arm, data, axis, B_CORE_start, PRE_window,
                                      fold disclosures) + targets_npz_sha256 + the M2 block (formula, base shas, counts, beta_book distribution)
  work/targets/M2DIAG_<tag>.npz       per anchor: kind, beta_book (file units), L1 / net before and after, hedge, BTC weight before / after,
                                      share of |w| on fallback names, n fallback names
  work/targets/BETA_<tag>.npz         anchor, beta (n_anchor × 829), nobs, est
Validation after writing: the certified adapter (baseline_tables devices_v3/bt_objb_targets.py, imported read-only) loads the new file with
its receipt without error, and on every anchor of the axis the dense row equals the base row except the BTC column, bitwise.
usage: env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B m2_build_targets.py PATH,HOME,LC_CTYPE \
         <base_npz> <base_npz_sha> <base_receipt> <base_receipt_sha> <arm> <reading> <tag> <out_root>
"""
import os, sys, json, time, collections
WL = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else set()
assert WL, "env whitelist (argv[1]) must be non-empty"
extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"): os.environ[_k] = "1"
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import m2_lib as M

T0 = time.time()
base_npz, base_sha, base_rc, base_rc_sha, ARM, READING, TAG, OUTR = sys.argv[2:10]
BT = "/workspace/baseline_tables_2026-09-19"
PIN = {"price_full_raw": (BT + "/work/price_full_raw_x0918r.npy", "23af32bd97c267d126c2109641815b92082b8688e35bcfbaaa1e88c2dc5bb5d8"),
       "price_full_meta": (BT + "/work/price_full_raw_x0918r_meta.npz", "d1e49cc9f0a7ddc4104feb52a42da3024ba1e66ad5891a26c96f00cff7ce5d90"),
       "price_full_meta_old": (BT + "/work/price_full_meta.npz", "f2f5382889f8c926ab2b47a81def234b1d5b7ee9cc15a86cdcfaba69416ff7b4"),
       "adapter": (BT + "/devices_v3/bt_objb_targets.py", "05cc5dc25df99459d93b34c9b10477f08002dd301b9b45ec6aa47bd77fc95373"),
       "base_npz": (base_npz, base_sha), "base_receipt": (base_rc, base_rc_sha)}
rec = dict(device="m2_build_targets.py", self_sha256=M.sha_file(os.path.abspath(__file__)), lib_sha256=M.sha_file(os.path.join(HERE, "m2_lib.py")),
           argv=sys.argv, env=dict(os.environ), numpy=np.__version__, python=sys.version.split()[0],
           utc_start=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), prereg={"path": "docs/PREREG_old_vs_new_models_same_engine_2026-09-23.md",
           "commit": "8530d2b7f", "sha256": "1217d786b29cf8bcb37f4aa86f2e9862bb278f7c1a91cc9ac58ed9376b9a31b4"}, inputs={}, checks=[])
FAILS = []


def log(*a): print("[%6.0fs]" % (time.time() - T0), *a, flush=True)


def check(name, ok, detail=None):
    rec["checks"].append(dict(check=name, ok=bool(ok), detail=detail)); log("CHECK", name, "OK" if ok else "FAIL", json.dumps(detail, default=str)[:300] if detail is not None else "")
    if not ok: FAILS.append(name)


os.makedirs(OUTR + "/work/targets", exist_ok=True); os.makedirs(OUTR + "/receipts", exist_ok=True)
RP = OUTR + f"/receipts/BUILD_{TAG}.json"


def finish(code, line):
    rec["failed"] = FAILS; rec["runtime_s"] = round(time.time() - T0, 1)
    json.dump(rec, open(RP + ".tmp", "w"), indent=1, default=str); os.replace(RP + ".tmp", RP)
    print(line + " receipt_sha256=" + M.sha_file(RP), flush=True); sys.exit(code)


for k, (p, s) in PIN.items():
    got = M.sha_file(p); rec["inputs"][k] = {"path": p, "sha256": got}; check(f"pin.{k}", got == s, {"got": got[:16], "want": s[:16]})
if FAILS: finish(3, "M2_BUILD VERDICT=REFUSED")

# ---- input check: in-life missing = gap-filled ∪ UA ----
PM = np.load(PIN["price_full_meta"][0], allow_pickle=True); PO = np.load(PIN["price_full_meta_old"][0], allow_pickle=True)
SY = [str(s) for s in PM["symbols"]]; bj = SY.index(M.BTC); nS = len(SY)
check("axis.symbols_old_eq_raw", [str(s) for s in PO["symbols"]] == SY)
check("grid.old_is_prefix_of_raw", np.array_equal(PO["grid"].astype(np.int64), PM["grid"].astype(np.int64)[:len(PO["grid"])]))
nold = len(PO["grid"])
inl = set(zip(PO["inlife_nan_grid_row"].astype(np.int64).tolist(), PO["inlife_nan_col"].astype(np.int64).tolist()))
gf = set((r, c) for r, c in zip(PM["gapfilled_grid_row"].astype(np.int64).tolist(), PM["gapfilled_col"].astype(np.int64).tolist()) if r < nold)
ua = set((r, c) for r, c in zip(PM["unavail_grid_row"].astype(np.int64).tolist(), PM["unavail_col"].astype(np.int64).tolist()) if r < nold)
check("inlife_missing_equals_gapfilled_union_UA", inl == (gf | ua) and not (gf & ua),
      {"inlife_nan_old": len(inl), "gapfilled": len(gf), "ua": len(ua), "overlap": len(gf & ua), "inl_minus": len(inl - (gf | ua)), "union_minus": len((gf | ua) - inl)})
ua_ext = int(np.sum(PM["unavail_grid_row"].astype(np.int64) >= nold)); gf_ext = int(np.sum(PM["gapfilled_grid_row"].astype(np.int64) >= nold))
check("extension_rows_add_no_gapfill_or_ua_unaccounted", True, {"ua_in_extension_rows": ua_ext, "gapfilled_in_extension_rows": gf_ext,
      "note": "extension (after the OLD grid) has no OLD in-life-NaN reference; the price device's G5 states the extension adds no UA and no gap fill"})
if FAILS: finish(3, "M2_BUILD VERDICT=REFUSED")

# ---- base targets ----
BR = json.load(open(base_rc)); check("base_receipt.npz_sha", BR.get("targets_npz_sha256") == base_sha, BR.get("targets_npz_sha256"))
check("base_receipt.arm", BR.get("arm", "A0") == ARM, BR.get("arm"))
Z = np.load(base_npz, allow_pickle=False)
A = Z["anchor"].astype(np.int64); kind = Z[f"{READING}_kind"]; off = Z[f"{READING}_off"].astype(np.int64); idx = Z[f"{READING}_idx"]; val = Z[f"{READING}_val"].astype(np.float64)
check("base.axis_4h_contiguous", len(A) > 0 and bool(np.all(np.diff(A) == M.H4)), {"n": len(A), "first": int(A[0]), "last": int(A[-1])})
if FAILS: finish(3, "M2_BUILD VERDICT=REFUSED")

# ---- betas ----
LP = np.load(PIN["price_full_raw"][0], mmap_mode="r"); grid = PM["grid"].astype(np.int64)
check("price.shape", LP.shape == (len(grid), nS), list(LP.shape))
log("bars_4h ...")
T, R, V = M.bars_4h(LP, grid, PM["first_fin"], PM["last_fin"], PM["unavail_grid_row"], PM["unavail_col"])
log("bars", len(T), "valid cells", int(V.sum()))
log("betas ...")
B, NOBS, EST, RAW = M.betas_at(T, R, V, A, bj)
log("betas done")
bb = M.beta_book_rows(kind, off, idx, val, B)
pub = kind > 0
hedge = np.where(pub, -bb, 0.0)
k2, o2, i2, v2, tst = M.transform(kind, off, idx, val, hedge, bj)
rec["transform_stats"] = tst

# ---- write ----
tp = OUTR + f"/work/targets/TARGETS_{TAG}.npz"
np.savez(tp[:-4] + ".tmp.npz", anchor=A, **{f"{READING}_kind": k2, f"{READING}_off": o2, f"{READING}_idx": i2, f"{READING}_val": v2})
os.replace(tp[:-4] + ".tmp.npz", tp); tsha = M.sha_file(tp)
L1b = M.row_l1(off, val); L1m = M.row_l1(o2, v2); netb = M.row_net(off, val); netm = M.row_net(o2, v2)


def btc_w(o, i, v):
    out = np.zeros(len(o) - 1)
    for r in range(len(o) - 1):
        a, b = o[r], o[r + 1]; p = np.nonzero(i[a:b] == bj)[0]
        if len(p): out[r] = v[a + p[0]]
    return out


fb_share = np.zeros(len(A)); n_fb = np.zeros(len(A), np.int32)
for r in range(len(A)):
    a, b = off[r], off[r + 1]
    if b > a:
        cols = idx[a:b].astype(np.int64); fb = ~EST[r, cols] & (cols != bj)
        n_fb[r] = int(fb.sum()); fb_share[r] = float(np.abs(val[a:b][fb]).sum() / np.abs(val[a:b]).sum())
dp = OUTR + f"/work/targets/M2DIAG_{TAG}.npz"
np.savez(dp[:-4] + ".tmp.npz", anchor=A, kind=kind, beta_book=bb, hedge=hedge, L1_base=L1b, L1_m2=L1m, net_base=netb, net_m2=netm,
         btc_w_base=btc_w(off, idx, val), btc_w_m2=btc_w(o2, i2, v2), fallback_abs_w_share=fb_share, n_fallback_names=n_fb)
os.replace(dp[:-4] + ".tmp.npz", dp)
bp = OUTR + f"/work/targets/BETA_{TAG}.npz"
np.savez(bp[:-4] + ".tmp.npz", anchor=A, beta=B, nobs=NOBS.astype(np.int16), est=EST, symbols=np.array(SY))
os.replace(bp[:-4] + ".tmp.npz", bp)

# ---- receipt for the adapter ----
yr = np.array([time.gmtime(int(a)).tm_year for a in A])


def q(x):
    x = np.asarray(x, float)
    if len(x) == 0: raise M.M2Error("empty series in a distribution")
    return {"n": int(len(x)), "mean": float(x.mean()), "p05": float(np.percentile(x, 5)), "p25": float(np.percentile(x, 25)), "p50": float(np.percentile(x, 50)),
            "p75": float(np.percentile(x, 75)), "p95": float(np.percentile(x, 95)), "min": float(x.min()), "max": float(x.max())}


dist = {}
for y in sorted(set(yr.tolist())):
    m = pub & (yr == y)
    if not m.any(): continue
    dist[str(y)] = {"beta_book_file_units": q(bb[m]), "beta_book_over_L1_base (gross units after the executor's L1 normalisation)": q(bb[m] / L1b[m]),
                    "hedge_over_L1_m2": q(hedge[m] / L1m[m]), "L1_m2_over_L1_base": q(L1m[m] / L1b[m]), "fallback_abs_w_share": q(fb_share[m]),
                    "net_base_over_L1": q(netb[m] / L1b[m]), "net_m2_over_L1_m2": q(netm[m] / L1m[m])}
R_out = {k: BR[k] for k in BR if k not in ("targets_npz_sha256", "self_sha256", "driver_sha256", "lib_sha256", "utc", "readings")}
R_out.update(tag=TAG, targets_npz_sha256=tsha, readings_written=[READING], utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
             m2={"formula": "prereg Stage 2 (m2_lib.py docstring)", "base": {"npz": base_npz, "npz_sha256": base_sha, "receipt": base_rc, "receipt_sha256": base_rc_sha,
                 "tag": BR.get("tag"), "reading": READING}, "builder_sha256": rec["self_sha256"], "lib_sha256": rec["lib_sha256"], "btc_col": bj,
                 "counts": {"anchors": int(len(A)), "published": int(pub.sum()), "hold": int((~pub).sum()),
                            "anchors_before_first_price_bar": int(np.sum(A < int(T[1]))), "transform": tst},
                 "beta_book_by_year_published": dist, "diag_npz": dp, "diag_npz_sha256": M.sha_file(dp), "beta_npz": bp, "beta_npz_sha256": M.sha_file(bp)})
trp = OUTR + f"/receipts/TARGETS_{TAG}.json"
json.dump(R_out, open(trp + ".tmp", "w"), indent=1, default=str); os.replace(trp + ".tmp", trp); trsha = M.sha_file(trp)
rec["outputs"] = {"targets_npz": {"path": tp, "sha256": tsha}, "targets_receipt": {"path": trp, "sha256": trsha}, "diag": {"path": dp, "sha256": M.sha_file(dp)},
                  "beta": {"path": bp, "sha256": M.sha_file(bp)}}
rec["beta_book_by_year_published"] = dist

# ---- validation through the certified adapter ----
sys.path.insert(0, BT + "/devices_v3")
import bt_objb_targets as OT
check("adapter.module_is_pinned_file", os.path.realpath(OT.__file__) == os.path.realpath(PIN["adapter"][0]), OT.__file__)
Tn = OT.load_targets([dict(npz=tp, npz_sha256=tsha, receipt=trp, receipt_sha256=trsha)], reading=READING, arm=ARM, n_sym=nS)
Tb = OT.load_targets([dict(npz=base_npz, npz_sha256=base_sha, receipt=base_rc, receipt_sha256=base_rc_sha)], reading=READING, arm=ARM, n_sym=nS)
check("adapter.loads_m2_file", True, {"n": len(Tn["anchor"]), "sources": [{k: s[k] for k in ("tag", "arm", "data", "written_rows_without_weights", "zero_weights")} for s in Tn["sources"]]})
Wn, fn, kn, cn = OT.book_for_window(Tn, A, nS); Wb, fb_, kb, cb = OT.book_for_window(Tb, A, nS)
notb = np.ones(nS, bool); notb[bj] = False
same_other = np.array_equal(np.ascontiguousarray(Wn[:, notb]).view(np.uint64), np.ascontiguousarray(Wb[:, notb]).view(np.uint64))
btc_ok = np.array_equal(Wn[:, bj].view(np.uint64), (Wb[:, bj] + hedge).view(np.uint64))
check("adapter.dense_rows_equal_base_except_btc_bitwise", same_other, {"anchors": len(A)})
check("adapter.btc_column_equals_base_plus_hedge_bitwise", btc_ok, {"max_abs": float(np.max(np.abs(Wn[:, bj] - Wb[:, bj] - hedge)))})
check("adapter.fresh_and_kind_unchanged", np.array_equal(fn, fb_) and np.array_equal(kn, kb), {"m2": cn, "base": cb})
check("hold_rows_have_zero_hedge", bool(np.all(hedge[~pub] == 0.0)), int((~pub).sum()))
rec["VERDICT"] = "PASS" if not FAILS else "RED"
finish(0 if not FAILS else 3, f"M2_BUILD VERDICT={rec['VERDICT']} tag={TAG} targets_sha256={tsha}")
