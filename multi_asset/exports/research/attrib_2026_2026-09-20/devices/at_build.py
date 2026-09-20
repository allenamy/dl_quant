#!/usr/bin/env python3
"""at_build.py — builds the per-(anchor, name) L2 PAPER panel the attribution is cut from.

Every definition it uses is the frozen one in at_lib's header and in RUN_CONFIG_attrib_2026-09-20.json, which
at_prerun wrote before this device ever ran. This device computes VALUES ONLY: books, returns, funding,
characteristics, conditions. It computes no group, no period aggregate and no contrast — those are at_attrib's.

Axis: the A0_ext anchors that lie inside the certified price grid, 2022-06-30T00:00Z → 2026-09-18T20:00Z
(9,252). The first 9,139 are exactly the certified run's window; the remaining 113 are the extension, carried
so that §2-G can say where the book stands on 2026-09-18 — they are marked and never merged into a
FULL_RECIPE number.

GATES DECLARED HERE, BEFORE THE FIRST RUN (a failed gate ⇒ the per-name layer is reported UNAVAILABLE, not
patched):
  B1 Σ|W| = 1 on every anchor with a non-empty written population (|Σ|W|−1| ≤ 1e-12).
  B2 ΣW = 0 on the same anchors (|ΣW| ≤ 1e-12) — the executor's re-demeaning.
  B3 on every anchor whose written file is the king file, W == reshape(king_file) bitwise.
  B4 A2 is exactly additive: Σ_i s_i·W_i·x + Σ_i (1−s_i)·W_i·x − Σ_i W_i·x = 0 (≤ 1e-12 in bps) for x = RET.
  B5 A2b is exactly additive: A1_king + A1_fund + shape residual − paper price = 0 (≤ 1e-12 bps).
  B6 market + selection = price per anchor (≤ 1e-9 bps).
  B7 the paper layer tracks the realised layer: Pearson r ≥ 0.80 between the per-anchor paper price and the
     realised price over FULL_RECIPE, and likewise ≥ 0.80 for funding paid. (Level differences are the
     execution residual and are reported, not gated.)
  B8 MOM30 from the certified price table agrees with the c0 channel (meta_newprod_v4 y4) on the overlap:
     Pearson r ≥ 0.98 over member cells where both are finite.
  B9 every anchor's characteristic NaN share among members < 0.05, except AGE's left-censored flag and the
     first 180 anchors of MOM30 (no 30-day history in the price grid), both of which are reported by name.

usage: python at_build.py <ENV_WHITELIST_CSV> <OUT_DIR>
"""
import json, os, sys, time, zipfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import at_lib as L

T0 = time.time()
ENV_OK = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else set()
OUT = sys.argv[2] if len(sys.argv) > 2 else f"{L.ROOT}/receipts"
os.makedirs(OUT, exist_ok=True)
os.makedirs(f"{L.ROOT}/work", exist_ok=True)
chk = L.Checks(T0)
rec = L.rec_head("at_build.py", sys.argv)
chk("env.whitelist", not sorted(set(rec["env"]) - ENV_OK), {"extra": sorted(set(rec["env"]) - ENV_OK)})
CFGP = f"{L.ROOT}/RUN_CONFIG_attrib_2026-09-20.json"
chk("frozen_config.exists", os.path.exists(CFGP))
rec["frozen_config"] = {"path": CFGP, "sha256": L.sha(CFGP) if os.path.exists(CFGP) else None}
rec["inputs"] = L.verify_pins(chk)
if chk.fails:
    L.write_receipt(rec, chk, f"{OUT}/AT_BUILD.json")
    print("AT_BUILD VERDICT=REFUSED failed=%s" % chk.fails, flush=True)
    sys.exit(3)

NW = L.NW
# ─────────────────────────── axis ───────────────────────────
TX = np.load(L.PINS["TARGETS_A0_EXT"][0], allow_pickle=True)
PX = np.load(L.PINS["P3VEC_A0_EXT"][0], allow_pickle=True)
P3J = json.load(open(L.PINS["P3JSON_A0_EXT"][0]))["records"]
AGG = np.load(L.PINS["AGG_A0"][0], allow_pickle=True)
A_RUN = AGG["A"].astype(np.int64)
anch_all = TX["anchor"].astype(np.int64)
PME = np.load(L.PINS["PRICE_META"][0], allow_pickle=True)
G = PME["grid"].astype(np.int64)
SY = [str(s) for s in PME["symbols"]]
lo_ts, hi_ts = int(A_RUN[0]), int(anch_all[-1])
sel = np.nonzero((anch_all >= lo_ts) & (anch_all <= hi_ts))[0]
A = anch_all[sel]
NA = len(A)
chk("axis.window", NA == 9252 and L.utc(A[0]) == "2022-06-30T00:00:00Z" and L.utc(A[-1]) == "2026-09-18T20:00:00Z",
    {"n": NA, "first": L.utc(A[0]), "last": L.utc(A[-1])})
in_run = np.isin(A, A_RUN)
chk("axis.run_prefix", bool(in_run[:len(A_RUN)].all() and not in_run[len(A_RUN):].any()), {"n_run": int(in_run.sum())})
chk("p3json.axis", len(P3J) == len(anch_all) and all(int(P3J[int(a)]["anchor"]) == int(anch_all[int(a)]) for a in sel[::37]),
    {"n_records": len(P3J), "n_anchors": int(len(anch_all))})

# ─────────────────────────── prices on the 4h sub-grid ───────────────────────────
chk("price.grid_starts_on_4h", (G[0] % L.H4) == 0, {"g0": L.utc(G[0])})
P = np.load(L.PINS["PRICE_FULL"][0], mmap_mode="r")
chk("price.shape", P.shape == (len(G), NW), {"shape": list(P.shape)})
r4 = np.arange(0, len(G), 48)
G4 = G[r4]
LP = np.asarray(P[::48], np.float64)          # (n4, 829) log price on the 4h grid
del P
chk("price.4h_rows", LP.shape[0] == len(G4), {"n4": int(LP.shape[0])})
g4row = {int(t): i for i, t in enumerate(G4)}
k0 = np.array([g4row[int(t)] for t in A], np.int64)
chk("price.exit_row_exists", int(k0[-1]) + 1 < LP.shape[0])
RET = np.expm1(LP[k0 + 1] - LP[k0]).astype(np.float64)        # (NA, 829)
FF = PME["first_fin"].astype(np.int64)
LF = PME["last_fin"].astype(np.int64)
INLIFE = (FF[None, :] <= A[:, None]) & (LF[None, :] >= (A[:, None] + L.H4))
# STRICT_OUT = the whole 4h window lies outside [first_fin, last_fin]. There the cumulated log-price is flat
# by construction and the return must be exactly 0. The remaining ~1 anchor per name is the LISTING (or
# delisting) window, where first_fin or last_fin falls inside (E, E+4h]: there the table does move, the name
# is not yet (or no longer) a full-window instrument, and INLIFE excludes it. Counted and reported, not hidden.
STRICT_OUT = (FF[None, :] > (A[:, None] + L.H4)) | (LF[None, :] < A[:, None])
chk("price.strictly_dead_rows_are_flat", float(np.abs(RET[STRICT_OUT]).max()) < 1e-12,
    {"max_abs_ret": float(np.abs(RET[STRICT_OUT]).max()), "cells": int(STRICT_OUT.sum())})
trans = (~INLIFE) & (~STRICT_OUT) & (np.abs(RET) > 1e-12)
rec["price_listing_transition_cells"] = {"cells": int(trans.sum()), "names": int((trans.any(0)).sum()),
                                         "max_abs_ret": float(np.abs(RET[trans]).max()) if trans.any() else 0.0}
RET = np.where(INLIFE, RET, 0.0)
# MOM30 = 180 4h intervals back, on the same table
MOM30 = np.full((NA, NW), np.nan)
ok180 = k0 - 180 >= 0
if ok180.any():
    kk = k0[ok180]
    m = np.expm1(LP[kk] - LP[kk - 180])
    live = (FF[None, :] <= (A[ok180][:, None] - 180 * L.H4)) & (LF[None, :] >= A[ok180][:, None])
    MOM30[ok180] = np.where(live, m, np.nan)
rec["mom30_first_anchors_without_history"] = int((~ok180).sum())
del LP

# ─────────────────────────── funding over (E, E+4h] ───────────────────────────
LED = np.load(L.PINS["LEDGER_SPLICED"][0], allow_pickle=True)
off = LED["off"].astype(np.int64)
ft = LED["ft"].astype(np.int64)
rate = np.asarray(LED["rate"], np.float64)
ziv = np.asarray(LED["zip_iv"], np.float64)
FUND = np.zeros((NA, NW))
RN8_LED = np.full((NA, NW), np.nan)
unsorted = 0
for j in range(NW):
    i0, i1 = int(off[j]), int(off[j + 1])
    if i1 <= i0:
        continue
    t = ft[i0:i1]
    if not bool((np.diff(t) > 0).all()):
        unsorted += 1
        continue
    r_ = rate[i0:i1]
    cs = np.concatenate([[0.0], np.cumsum(r_)])
    lo = np.searchsorted(t, A, side="right")          # settlements with ft <= E
    hi = np.searchsorted(t, A + L.H4, side="right")   # settlements with ft <= E+4h
    FUND[:, j] = cs[hi] - cs[lo]
    prev = lo - 1
    okp = prev >= 0
    iv = np.where(np.isfinite(ziv[i0:i1]) & (ziv[i0:i1] > 0), ziv[i0:i1], 8.0)
    RN8_LED[okp, j] = r_[prev[okp]] * (8.0 / iv[prev[okp]])
chk("funding.settlements_strictly_sorted_per_symbol", unsorted == 0, {"n_symbols_unsorted": int(unsorted)})
chk("funding.nonzero_cells", float(np.abs(FUND).sum()) > 0, {"nonzero_cells": int((FUND != 0).sum())})

# ─────────────────────────── books ───────────────────────────
W = np.zeros((NA, NW))
AK = np.zeros((NA, NW))     # a_i  (king part of the mix, demeaned, un-normalised)
BF = np.zeros((NA, NW))     # b_i  (fund part)
SHARE = np.zeros((NA, NW))  # s_i
LMIX = np.zeros(NA)         # L = Σ|a+b|
KIND = np.zeros(NA, np.int8)
PHI = np.zeros((NA, 2))     # [φ_king, φ_fund]
MEMB = np.zeros((NA, NW), bool)
NPOP = np.zeros(NA, np.int32)
g1 = g2 = g3 = 0.0
b3_bad = 0
# materialise every CSR array ONCE: an NpzFile re-decompresses the whole array on each key access, which
# inside a 9,252-iteration loop costs minutes per key and hides the real work.
CS = {k: np.asarray(TX[k]) for k in ("scaled_off", "scaled_idx", "scaled_val", "scaled_kind")}
for pref in ("kc", "fc", "king_file", "combo", "king"):
    for suf in ("_off", "_idx", "_val"):
        CS[pref + suf] = np.asarray(PX[pref + suf])
CS["pm_off"] = np.asarray(PX["pm_off"])
CS["pm"] = np.asarray(PX["pm"])
for i, a in enumerate(sel):
    o0, o1 = int(CS["scaled_off"][a]), int(CS["scaled_off"][a + 1])
    ii = CS["scaled_idx"][o0:o1]
    vv = CS["scaled_val"][o0:o1]
    kind = int(CS["scaled_kind"][a])
    KIND[i] = kind
    pmi = CS["pm"][int(CS["pm_off"][a]):int(CS["pm_off"][a + 1])]
    MEMB[i, pmi] = True
    if len(ii) == 0:
        continue
    NPOP[i] = len(ii)
    w = L.reshape_pop(vv)
    W[i, ii] = w
    g1 = max(g1, abs(abs(w).sum() - 1.0))
    g2 = max(g2, abs(w.sum()))
    # seats
    if kind == 1:
        phik, phif = 1.0, 0.0
        kc = L.csr_dense(CS, "king_file", a)
        fc = np.zeros(NW)
        tgt = np.zeros(NW)
        tgt[ii] = vv
        if not np.array_equal(tgt.view(np.uint64), kc.view(np.uint64)):
            b3_bad += 1
    else:
        cm = (P3J[a]["combo"].get("combo_meta") or {})
        w3 = cm.get("w3_masked") or [np.nan, np.nan, np.nan]
        phik, phif = float(w3[0]), float(w3[2])
        kc = L.csr_dense(CS, "kc", a)
        fc = L.csr_dense(CS, "fc", a)
    PHI[i] = (phik, phif)
    pop = (np.abs(phik * kc) > 0) | (np.abs(phif * fc) > 0)
    if pop.any():
        a_ = np.zeros(NW)
        b_ = np.zeros(NW)
        a_[pop] = phik * (kc[pop] - (kc[pop].mean() if phik != 0 else 0.0))
        b_[pop] = phif * (fc[pop] - (fc[pop].mean() if phif != 0 else 0.0))
        m_ = a_ + b_
        Lm = np.abs(m_).sum()
        LMIX[i] = Lm
        AK[i] = a_
        BF[i] = b_
        s = np.full(NW, phik / (phik + phif) if (phik + phif) > 0 else 1.0)
        big = np.abs(m_) >= L.EPS_SHARE
        s[big] = a_[big] / m_[big]
        SHARE[i] = s
    if i % 1000 == 0:
        chk.log("book", i, "/", NA, L.utc(A[i]), "rss", round(L.rss_gb(), 2))
chk("B1.unit_gross", g1 <= 1e-12, {"max_abs_dev": float(g1)})
chk("B2.zero_net", g2 <= 1e-12, {"max_abs_net": float(g2)})
chk("B3.king_file_anchors_write_the_king_file", b3_bad == 0, {"n_bad": int(b3_bad), "n_kind1": int((KIND == 1).sum())})
chk("B3b.seats_finite", bool(np.isfinite(PHI).all()), {"n_nonfinite": int((~np.isfinite(PHI)).sum())})
chk("book.every_anchor_has_a_population", int((NPOP == 0).sum()) == 0, {"n_empty": int((NPOP == 0).sum())})
chk("book.mix_population_nonempty", int((LMIX <= 0).sum()) == 0, {"n_zero_L": int((LMIX <= 0).sum())})

# additivity gates (on RET)
px_paper = 1e4 * (W * RET).sum(1)
a2k = 1e4 * (SHARE * W * RET).sum(1)
a2f = 1e4 * ((1.0 - SHARE) * W * RET).sum(1)
with np.errstate(all="ignore"):
    a1k = 1e4 * (AK * RET).sum(1) / np.where(LMIX > 0, LMIX, np.nan)
    a1f = 1e4 * (BF * RET).sum(1) / np.where(LMIX > 0, LMIX, np.nan)
    shp = px_paper - a1k - a1f
chk("B4.A2_additive", float(np.nanmax(np.abs(a2k + a2f - px_paper))) <= 1e-9, {"max_abs_bps": float(np.nanmax(np.abs(a2k + a2f - px_paper)))})
chk("B5.A2b_additive", float(np.nanmax(np.abs(a1k + a1f + shp - px_paper))) <= 1e-9, {"max_abs_bps": float(np.nanmax(np.abs(a1k + a1f + shp - px_paper)))})

# market / selection: the PRICED set Q = in-life names (RET is identically 0 elsewhere, so they contribute
# nothing to price and must contribute nothing to either half — c0's "y4 missing ⇒ both terms 0").
LIVEM = MEMB & INLIFE
nm_ = LIVEM.sum(1)
YBAR = np.where(nm_ > 0, (np.where(LIVEM, RET, 0.0)).sum(1) / np.maximum(nm_, 1), np.nan)
NETQ = (W * INLIFE).sum(1)                  # the priced part's net exposure (ΣW = 0 over the whole book)
yb0 = np.where(np.isfinite(YBAR), YBAR, 0.0)
mkt = 1e4 * NETQ * yb0
selc = 1e4 * (W * INLIFE * (RET - yb0[:, None])).sum(1)        # computed independently, NOT as price − market
chk("B6.market_plus_selection", float(np.nanmax(np.abs(mkt + selc - px_paper))) <= 1e-9,
    {"max_abs_bps": float(np.nanmax(np.abs(mkt + selc - px_paper)))})
chk("universe.members_per_anchor", int(nm_[in_run].min()) > 50, {"min": int(nm_[in_run].min()), "median": float(np.median(nm_[in_run]))})

# ─────────────────────────── B7: paper vs realised ───────────────────────────
L1 = np.load(f"{L.ROOT}/work/AT_L1_mean.npz")
assert np.array_equal(L1["A"].astype(np.int64), A_RUN)
fd_paper = 1e4 * (W * FUND).sum(1)
mfr = L.period_mask(A, "2023-06-30T04:00:00Z", "2026-08-31T00:00:00Z")
mfr_run = L.period_mask(A_RUN, "2023-06-30T04:00:00Z", "2026-08-31T00:00:00Z")
rp = float(np.corrcoef(px_paper[mfr], L1["price"][mfr_run])[0, 1])
rf = float(np.corrcoef(fd_paper[mfr], L1["funding_paid"][mfr_run])[0, 1])
chk("B7.paper_tracks_realised_price", rp >= 0.80, {"pearson": rp})
chk("B7.paper_tracks_realised_funding", rf >= 0.80, {"pearson": rf})
rec["B7"] = {"pearson_price": rp, "pearson_funding": rf,
             "mean_paper_price_bps": float(px_paper[mfr].mean()), "mean_realised_price_bps": float(L1["price"][mfr_run].mean()),
             "mean_paper_funding_bps": float(fd_paper[mfr].mean()), "mean_realised_funding_bps": float(L1["funding_paid"][mfr_run].mean())}

# ─────────────────────────── characteristics ───────────────────────────
PAN = np.load(L.PINS["PANEL_X0918"][0], allow_pickle=True)
PTS = PAN["ts"].astype(np.int64)
prow = {int(t): i for i, t in enumerate(PTS)}
pj = np.array([prow.get(int(t), -1) for t in A], np.int64)
haspan = pj >= 0
chk("panel.rows_missing_are_extension_only", bool(haspan[in_run].all()),
    {"n_missing": int((~haspan).sum()), "missing": [L.utc(t) for t in A[~haspan]][:12],
     "note": "the x0918 panel ends 2026-09-18T00:00Z; RN8 is NaN on any later extension anchor"})
pjs = np.where(haspan, pj, 0)
fn = np.asarray(PAN["f_fund_now"], np.float64)[pjs]
iv = np.asarray(PAN["f_fund_iv"], np.float64)[pjs]
RN8 = fn * (8.0 / np.where(np.isfinite(iv) & (iv > 0), iv, 8.0))
RN8[~haspan] = np.nan
ok_x = np.isfinite(RN8) & np.isfinite(RN8_LED) & LIVEM
rec["RN8_crosscheck_vs_ledger"] = {"cells": int(ok_x.sum()),
                                   "pearson": float(np.corrcoef(RN8[ok_x], RN8_LED[ok_x])[0, 1]) if ok_x.sum() > 100 else None,
                                   "mean_abs_diff_bp": float(np.abs(RN8[ok_x] - RN8_LED[ok_x]).mean() * 1e4) if ok_x.sum() else None}
MOM30_PANEL = np.asarray(PAN["f_mom_30d"], np.float64)[pjs]
MOM30_PANEL[~haspan] = np.nan
ok_m = np.isfinite(MOM30) & np.isfinite(MOM30_PANEL) & LIVEM
rec["MOM30_crosscheck_vs_panel"] = {"cells": int(ok_m.sum()),
                                    "pearson": float(np.corrcoef(MOM30[ok_m], MOM30_PANEL[ok_m])[0, 1]) if ok_m.sum() > 100 else None}
del PAN, fn, iv, MOM30_PANEL

# B8: the c0 channel itself (meta_newprod_v4 y4)
MT = np.load(L.PINS["META_V4"][0], allow_pickle=True)
ME = MT["E_ts"].astype(np.int64)
Y4 = np.asarray(MT["y4"], np.float64)
mrow = {int(t): i for i, t in enumerate(ME)}
LY = np.where(np.isfinite(Y4), np.log1p(np.where(np.isfinite(Y4), Y4, 0.0)), 0.0)
BADY = ~np.isfinite(Y4)
cLY = np.vstack([np.zeros((1, NW)), np.cumsum(LY, 0)])
cBY = np.vstack([np.zeros((1, NW), np.int64), np.cumsum(BADY, 0)])
have = np.array([int(t) in mrow for t in A])
MOM30_META = np.full((NA, NW), np.nan)
for i in np.nonzero(have)[0]:
    r_ = mrow[int(A[i])]
    if r_ - 180 < 0:
        continue
    s = cLY[r_] - cLY[r_ - 180]
    bb = cBY[r_] - cBY[r_ - 180]
    MOM30_META[i] = np.where(bb == 0, np.expm1(s), np.nan)
ok_b8 = np.isfinite(MOM30) & np.isfinite(MOM30_META) & LIVEM
r_b8 = float(np.corrcoef(MOM30[ok_b8], MOM30_META[ok_b8])[0, 1]) if ok_b8.sum() > 100 else None
chk("B8.MOM30_matches_c0_channel", (r_b8 is not None) and r_b8 >= 0.98,
    {"pearson": r_b8, "cells": int(ok_b8.sum()),
     "p99_abs_diff": float(np.percentile(np.abs(MOM30[ok_b8] - MOM30_META[ok_b8]), 99)) if ok_b8.sum() else None})
del MT, Y4, LY, BADY, cLY, cBY, MOM30_META

# cache-derived: AGE / LIQ / TBF
CP = L.PINS["CACHE_X0918R"][0]
CZ = np.load(CP, allow_pickle=True)
CTS = CZ["ts"].astype(np.int64)
crow = {int(t): i for i, t in enumerate(CTS)}
NR = len(CTS)
NB = (NR - 1) // 48
chk("cache.exact_buckets", 1 + NB * 48 == NR, {"rows": NR, "buckets": NB})
sum_qv = np.zeros((NB, NW))
n_qv = np.zeros((NB, NW), np.int32)
sum_tb = np.zeros((NB, NW))
n_tb = np.zeros((NB, NW), np.int32)
first_row = np.full(NW, -1, np.int64)
zf = zipfile.ZipFile(CP)
with zf.open("data.npy") as fh:
    ver = np.lib.format.read_magic(fh)
    shape, fort, dt = (np.lib.format.read_array_header_1_0(fh) if ver == (1, 0) else np.lib.format.read_array_header_2_0(fh))
    assert (not fort) and shape == (NR, NW, 7), (shape, fort)
    rowb = NW * 7 * dt.itemsize
    buf = fh.read(rowb)
    X = np.frombuffer(buf, dt).reshape(1, NW, 7)
    lc = X[:, :, 4].astype(np.float32)
    tr = np.isfinite(lc) & (lc > 0)
    first_row[tr[0] & (first_row < 0)] = 0
    r = 1
    BLK = 48 * 128
    while r < NR:
        k = min(BLK, NR - r)
        buf = fh.read(k * rowb)
        assert len(buf) == k * rowb
        X = np.frombuffer(buf, dt).reshape(k, NW, 7)
        lq = X[:, :, 3].astype(np.float64)
        lc = X[:, :, 4].astype(np.float32)
        tb = X[:, :, 6].astype(np.float64)
        tr = np.isfinite(lc) & (lc > 0)
        has = tr.any(0)
        newf = has & (first_row < 0)
        if newf.any():
            first_row[newf] = r + np.argmax(tr[:, newf], axis=0)
        okq = np.isfinite(lq)
        vol = np.where(okq, np.expm1(np.where(okq, lq, 0.0)), 0.0)
        okt = np.isfinite(tb) & tr
        nbk = k // 48
        j0 = (r - 1) // 48
        sum_qv[j0:j0 + nbk] += vol.reshape(nbk, 48, NW).sum(1)
        n_qv[j0:j0 + nbk] += okq.reshape(nbk, 48, NW).sum(1, dtype=np.int32)
        sum_tb[j0:j0 + nbk] += np.where(okt, tb, 0.0).reshape(nbk, 48, NW).sum(1)
        n_tb[j0:j0 + nbk] += okt.reshape(nbk, 48, NW).sum(1, dtype=np.int32)
        r += k
        if (r // BLK) % 20 == 0:
            chk.log("cache", r, "/", NR, "rss", round(L.rss_gb(), 2))
del X, buf, lq, lc, tb, vol, okq, okt, tr
cq = np.vstack([np.zeros((1, NW)), np.cumsum(sum_qv, 0)])
cn = np.vstack([np.zeros((1, NW), np.int64), np.cumsum(n_qv.astype(np.int64), 0)])
ct = np.vstack([np.zeros((1, NW)), np.cumsum(sum_tb, 0)])
cm_ = np.vstack([np.zeros((1, NW), np.int64), np.cumsum(n_tb.astype(np.int64), 0)])
del sum_qv, n_qv, sum_tb, n_tb
ka = np.array([crow[int(t)] // 48 for t in A], np.int64)
chk("cache.anchor_rows_aligned", all(crow[int(t)] % 48 == 0 for t in A))
chk("cache.24h_history_available", int(ka.min()) >= 6, {"min_bucket": int(ka.min())})
vq = cq[ka] - cq[ka - 6]
nq = cn[ka] - cn[ka - 6]
vt = ct[ka] - ct[ka - 6]
nt = cm_[ka] - cm_[ka - 6]
with np.errstate(all="ignore"):
    LIQ = np.where((nq >= 144) & (vq > 0), np.log(vq * 288.0 / np.maximum(nq, 1)), np.nan)
    TBF = np.where(nt >= 48, vt / np.maximum(nt, 1), np.nan)
del cq, cn, ct, cm_, vq, nq, vt, nt
first_ts = np.where(first_row >= 0, CTS[np.maximum(first_row, 0)], -1)
censored = first_row == 0
AGE = np.where(first_ts[None, :] >= 0, (A[:, None] - first_ts[None, :]) / 86400.0, np.nan)
rec["age_left_censored_names"] = int(censored.sum())

# B9
nanrep = {}
for nmx, X_ in (("RN8", RN8), ("MOM30", MOM30), ("LIQ", LIQ), ("TBF", TBF), ("AGE", AGE)):
    m_ = LIVEM & in_run[:, None]
    if nmx == "MOM30":
        m_ = m_ & ok180[:, None]
    nanrep[nmx] = float((~np.isfinite(X_[m_])).mean())
chk("B9.characteristic_nan_share_under_5pct", all(v < 0.05 for v in nanrep.values()), nanrep)

# ─────────────────────────── anchor conditions ───────────────────────────
GS = np.load(L.PINS["G0_STATE"][0], allow_pickle=True)
GL = np.load(L.PINS["G0_LABELS"][0], allow_pickle=True)
gts = GS["ts"].astype(np.int64)
gvars = [str(s) for s in GS["vars"]]
chk("g0.vars", gvars == list(L.G0_VARS), gvars)
chk("g0.axis_matches_labels", np.array_equal(gts, GL["ts"].astype(np.int64)))
grow2 = {int(t): i for i, t in enumerate(gts)}
gi = np.array([grow2[int(t)] for t in A], np.int64)
G0V = np.asarray(GS["EXCL"], np.float64)[gi]
G0V_INCL = np.asarray(GS["INCL"], np.float64)[gi]
G0L = np.asarray(GL["LAB_EXCL"], np.int8)[gi]
G0L_INCL = np.asarray(GL["LAB_INCL"], np.int8)[gi]
TURN = np.full(NA, np.nan)
TURN[in_run] = L1["turnover"]
COND = np.full((NA, len(L.COND_NAMES) + len(L.COND_EXTRA)), np.nan)
for ci, nmc in enumerate(list(L.COND_NAMES) + list(L.COND_EXTRA)):
    if nmc in L.COND_FROM_G0:
        COND[:, ci] = G0V[:, gvars.index(L.COND_FROM_G0[nmc])]
    elif nmc == "UBAR":
        COND[:, ci] = YBAR
    elif nmc == "TURN":
        COND[:, ci] = TURN
    else:
        raise SystemExit("unmapped condition " + nmc)

# ─────────────────────────── out ───────────────────────────
outp = f"{L.ROOT}/work/AT_PANEL.npz"
np.savez(outp + ".tmp.npz", A=A, symbols=np.array(SY), in_run=in_run, KIND=KIND, PHI=PHI, NPOP=NPOP,
         W=W.astype(np.float32), AK=AK.astype(np.float32), BF=BF.astype(np.float32), SHARE=SHARE.astype(np.float32),
         LMIX=LMIX, RET=RET.astype(np.float32), FUND=FUND.astype(np.float32), MEMB=MEMB, INLIFE=INLIFE,
         AGE=AGE.astype(np.float32), RN8=RN8.astype(np.float32), MOM30=MOM30.astype(np.float32),
         LIQ=LIQ.astype(np.float32), TBF=TBF.astype(np.float32), YBAR=YBAR,
         COND=COND, COND_NAMES=np.array(list(L.COND_NAMES) + list(L.COND_EXTRA)), NETQ=NETQ,
         G0V=G0V, G0V_INCL=G0V_INCL, G0L=G0L, G0L_INCL=G0L_INCL, G0_VARS=np.array(gvars),
         age_left_censored=censored, first_trade_ts=first_ts, ok180=ok180)
os.replace(outp + ".tmp.npz", outp)
rec["outputs"] = {"panel": {"path": outp, "sha256": L.sha(outp), "bytes": os.path.getsize(outp)}}
rec["summary_counts"] = {"n_anchors": int(NA), "n_in_run": int(in_run.sum()),
                         "kind_counts_in_run": {int(k): int((KIND[in_run] == k).sum()) for k in np.unique(KIND[in_run])},
                         "weight_on_out_of_life_share": float(np.abs(W[in_run])[~INLIFE[in_run]].sum() / np.abs(W[in_run]).sum()),
                         "weight_outside_member_set_share": float(np.abs(W[in_run])[~MEMB[in_run]].sum() / np.abs(W[in_run]).sum()),
                         "share_abs_max": float(np.abs(SHARE[W != 0]).max()),
                         "share_p99": float(np.percentile(np.abs(SHARE[W != 0]), 99))}

v = L.write_receipt(rec, chk, f"{OUT}/AT_BUILD.json", {"peak_rss_gb": L.rss_gb(), "runtime_s": round(time.time() - T0, 1)})
print("AT_BUILD VERDICT=%s checks=%d failed=%s" % (v, len(chk.rows), chk.fails), flush=True)
sys.exit(0 if v == "PASS" else 3)
