#!/usr/bin/env python3
"""m3_build_beta.py — the per-anchor β matrix M3 reads (prereg docs/PREREG_m3_beta_overlay_executed_book_2026-09-23.md §2 step 2: β_i exactly
as M2). DERIVED FROM the β part of m2_build_targets.py (M2, fcf80296); the formula lives in m2_lib.py (93f8e760, UNCHANGED, copied
sha-identical): 180 completed 4h bars ending at A, OLS slope with intercept of the name's 4h log return on BTCUSDT's, >= 120 valid pairs
else 1.0, clipped to [−1, 4], BTC = 1; missing intervals (outside [first_fin, last_fin], or any UNAVAILABLE 5-minute bar closing in the
closed 4h interval) excluded, never zero-filled.
Differences from M2's build (and nothing else): (1) the anchor axis is the WHOLE run window of the M3 configs (2022-06-30T00Z →
2026-09-18T20Z, 9,252 anchors; M2's stopped at 2026-08-31T00Z) and β is kept for EVERY symbol at every anchor (the executed target can hold
names the published row does not, e.g. clamped held names); (2) no target file is written (M3's hedge is computed at run time by m3_hook.py);
(3) cross-check: on the 9,139 anchors shared with M2's BETA_A0_main_M2.npz (M2's axis also has 900 earlier rows, before 2022-06-30) the matrix, the valid-pair counts and the estimated flags must be
BITWISE equal (same formula, same table ⇒ same numbers).
Input check (M2's, verbatim): the OLD cache's in-life NaN cells = gap-filled ∪ UNAVAILABLE cells of the raw table, disjoint.
Outputs (<out_root>/work/BETA_M3_full.npz: anchor, beta, nobs int16, est, symbols) and <out_root>/receipts/M3_BUILD_BETA.json.
usage: env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B m3_build_beta.py PATH,HOME,LC_CTYPE <config_old> <config_new>
         <m2_beta_npz> <out_root>
"""
import os, sys, json, time, calendar
WL = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else set()
assert WL, "env whitelist (argv[1]) must be non-empty"
extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"): os.environ[_k] = "1"
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import m2_lib as M

T0 = time.time()
cfg_old, cfg_new, m2_beta, OUTR = sys.argv[2:6]
BT = "/workspace/baseline_tables_2026-09-19"
PIN = {"price_full_raw": (BT + "/work/price_full_raw_x0918r.npy", "23af32bd97c267d126c2109641815b92082b8688e35bcfbaaa1e88c2dc5bb5d8"),
       "price_full_meta": (BT + "/work/price_full_raw_x0918r_meta.npz", "d1e49cc9f0a7ddc4104feb52a42da3024ba1e66ad5891a26c96f00cff7ce5d90"),
       "price_full_meta_old": (BT + "/work/price_full_meta.npz", "f2f5382889f8c926ab2b47a81def234b1d5b7ee9cc15a86cdcfaba69416ff7b4"),
       "m2_lib": (os.path.join(HERE, "m2_lib.py"), "93f8e76088ca523158df4d3ddb12f4f3239d0b75e3e0f7362ecc9ced914c8c9d")}
rec = dict(device="m3_build_beta.py", self_sha256=M.sha_file(os.path.abspath(__file__)), argv=sys.argv, env=dict(os.environ), numpy=np.__version__,
           python=sys.version.split()[0], utc_start=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), inputs={}, checks=[])
FAILS = []


def log(*a): print("[%6.0fs]" % (time.time() - T0), *a, flush=True)


def check(name, ok, detail=None):
    rec["checks"].append(dict(check=name, ok=bool(ok), detail=detail)); log("CHECK", name, "OK" if ok else "FAIL", json.dumps(detail, default=str)[:300] if detail is not None else "")
    if not ok: FAILS.append(name)


os.makedirs(OUTR + "/work", exist_ok=True); os.makedirs(OUTR + "/receipts", exist_ok=True)
RP = OUTR + "/receipts/M3_BUILD_BETA.json"


def finish(code, line):
    rec["failed"] = FAILS; rec["runtime_s"] = round(time.time() - T0, 1)
    json.dump(rec, open(RP + ".tmp", "w"), indent=1, default=str); os.replace(RP + ".tmp", RP)
    print(line + " receipt_sha256=" + M.sha_file(RP), flush=True); sys.exit(code)


for k, (p, s) in PIN.items():
    got = M.sha_file(p); rec["inputs"][k] = {"path": p, "sha256": got}; check(f"pin.{k}", got == s, {"got": got[:16], "want": s[:16]})
for k, p in (("config_old", cfg_old), ("config_new", cfg_new), ("m2_beta", m2_beta)):
    rec["inputs"][k] = {"path": p, "sha256": M.sha_file(p)}
if FAILS: finish(3, "M3_BUILD_BETA VERDICT=REFUSED")


def ts(s): return calendar.timegm(time.strptime(s, "%Y-%m-%dT%H:%M:%SZ"))


CO, CN = json.load(open(cfg_old)), json.load(open(cfg_new))
check("windows_equal_old_new", CO["window"]["first_anchor"] == CN["window"]["first_anchor"] and CO["window"]["last_anchor"] == CN["window"]["last_anchor"]
      and CO["window"]["n_anchors"] == CN["window"]["n_anchors"], [CO["window"], CN["window"]])
for nm, C in (("old", CO), ("new", CN)):
    check(f"config_{nm}.price_pins_are_the_pinned_table", C["pins"]["price_full_raw"]["sha256"] == PIN["price_full_raw"][1]
          and C["pins"]["price_full_meta"]["sha256"] == PIN["price_full_meta"][1])
A = np.arange(ts(CO["window"]["first_anchor"]), ts(CO["window"]["last_anchor"]) + 1, M.H4, dtype=np.int64)
check("axis.n_anchors", len(A) == CO["window"]["n_anchors"], len(A))
if FAILS: finish(3, "M3_BUILD_BETA VERDICT=REFUSED")

# ---- input check (M2 verbatim): in-life missing = gap-filled ∪ UA ----
PM = np.load(PIN["price_full_meta"][0], allow_pickle=True); PO = np.load(PIN["price_full_meta_old"][0], allow_pickle=True)
SY = [str(s) for s in PM["symbols"]]; bj = SY.index(M.BTC); nS = len(SY)
check("axis.symbols_old_eq_raw", [str(s) for s in PO["symbols"]] == SY)
check("grid.old_is_prefix_of_raw", np.array_equal(PO["grid"].astype(np.int64), PM["grid"].astype(np.int64)[:len(PO["grid"])]))
nold = len(PO["grid"])
inl = set(zip(PO["inlife_nan_grid_row"].astype(np.int64).tolist(), PO["inlife_nan_col"].astype(np.int64).tolist()))
gf = set((r, c) for r, c in zip(PM["gapfilled_grid_row"].astype(np.int64).tolist(), PM["gapfilled_col"].astype(np.int64).tolist()) if r < nold)
ua = set((r, c) for r, c in zip(PM["unavail_grid_row"].astype(np.int64).tolist(), PM["unavail_col"].astype(np.int64).tolist()) if r < nold)
check("inlife_missing_equals_gapfilled_union_UA", inl == (gf | ua) and not (gf & ua),
      {"inlife_nan_old": len(inl), "gapfilled": len(gf), "ua": len(ua), "overlap": len(gf & ua)})
check("extension_rows_ua_and_gapfill_counted", True, {"ua_in_extension_rows": int(np.sum(PM["unavail_grid_row"].astype(np.int64) >= nold)),
      "gapfilled_in_extension_rows": int(np.sum(PM["gapfilled_grid_row"].astype(np.int64) >= nold))})
if FAILS: finish(3, "M3_BUILD_BETA VERDICT=REFUSED")

# ---- betas ----
LP = np.load(PIN["price_full_raw"][0], mmap_mode="r"); grid = PM["grid"].astype(np.int64)
check("price.shape", LP.shape == (len(grid), nS), list(LP.shape))
log("bars_4h ...")
T, R, V = M.bars_4h(LP, grid, PM["first_fin"], PM["last_fin"], PM["unavail_grid_row"], PM["unavail_col"])
check("price.last_4h_boundary_covers_last_anchor", int(T[-1]) >= int(A[-1]), {"T_last": int(T[-1]), "A_last": int(A[-1])})
log("bars", len(T), "valid cells", int(V.sum()))
B, NOBS, EST, RAW = M.betas_at(T, R, V, A, bj)
log("betas done")
check("beta.all_finite", bool(np.all(np.isfinite(B))))
check("beta.btc_column_exactly_1", bool(np.all(B[:, bj] == 1.0)))
check("beta.within_clip", bool(np.all((B >= M.CLIP_LO) & (B <= M.CLIP_HI))))
bp = OUTR + "/work/BETA_M3_full.npz"
np.savez(bp[:-4] + ".tmp.npz", anchor=A, beta=B, nobs=NOBS.astype(np.int16), est=EST, symbols=np.array(SY))
os.replace(bp[:-4] + ".tmp.npz", bp)
bsha = M.sha_file(bp); rec["outputs"] = {"beta_npz": {"path": bp, "sha256": bsha}}

# ---- cross-check vs M2's matrix on the shared anchors ----
Z2 = np.load(m2_beta); A2 = Z2["anchor"].astype(np.int64)
pos = {int(a): i for i, a in enumerate(A.tolist())}
shared = np.array([pos[int(a)] for a in A2 if int(a) in pos], np.int64); i2 = np.array([i for i, a in enumerate(A2.tolist()) if int(a) in pos], np.int64)
unshared = np.array([int(a) for a in A2 if int(a) not in pos], np.int64)      # M2's target axis starts earlier (its pre-window rows)
check("m2_crosscheck.shared_anchor_count", len(shared) == 9139 and bool(np.all(unshared < A[0])),
      {"shared": len(shared), "m2_anchors": len(A2), "m2_unshared_all_before_first_anchor": bool(np.all(unshared < A[0])), "n_unshared": int(len(unshared))})
check("m2_crosscheck.symbols_equal", [str(s) for s in Z2["symbols"]] == SY)
check("m2_crosscheck.beta_bitwise_equal", np.array_equal(np.ascontiguousarray(B[shared]).view(np.uint64), np.ascontiguousarray(Z2["beta"][i2]).view(np.uint64)))
check("m2_crosscheck.nobs_equal", np.array_equal(NOBS[shared].astype(np.int16), Z2["nobs"][i2]))
check("m2_crosscheck.est_equal", np.array_equal(EST[shared], Z2["est"][i2]))
yr = np.array([time.gmtime(int(a)).tm_year for a in A])
rec["est_share_by_year"] = {str(y): float(EST[yr == y].mean()) for y in sorted(set(yr.tolist()))}
rec["VERDICT"] = "PASS" if not FAILS else "RED"
finish(0 if not FAILS else 3, f"M3_BUILD_BETA VERDICT={rec['VERDICT']} beta_sha256={bsha}")
