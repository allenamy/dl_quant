#!/usr/bin/env python3
"""c0_chars.py — stream C0 step 2: causal name characteristics at every replay anchor E in [2025-01-01 00Z, UB = 2026-08-30 20Z] (+ the
30-day warm-up the momentum windows need is read from before 2025). VALUES ONLY: this device never reads the book weights W or any P&L;
it writes raw per-(anchor, name) characteristic values and member-count marginals, from which the cohort rules are frozen
(docs/RESULT_c0_attribution_2026-09-19.md §1) before any cohort P&L is computed. pod2, CPU, read-only; writes only OUT_DIR.

Characteristics (all use only data with bar close <= E, or labels realised by E):
  AGE    days since the name's first traded 5m bar in the arm's cache (holefix2 1d7f459d; bar = log_cnt (ch 4) finite and > 0; holefix-filled
         bars count, they are official data.binance.vision klines). The cache starts 2022-01-01 00:00Z ⇒ names already trading then are
         LEFT-CENSORED (flag saved); for every anchor >= 2025-01-01 a censored name is > 1,095 days old.
  RN8    current funding rate, 8h-equivalent = f_fund_now · 8 / f_fund_iv (iv NaN or <= 0 → 8), the arm's panel (5e67c055) row of E — the same
         quantity as the arm's carry and FTRIM (w10_health.py L75, L211) and G0's RG-FLEVEL.
  MOM7 / MOM30  Π(1 + y4[E − n·4h]) − 1, n = 1..42 / 1..180, from meta_newprod_v4 y4 (RAW, UNCLIPPED accounting labels; y4 at E' covers
         bar closes in (E', E'+4h], realised by E' + 4h <= E). All intervals must be finite, else NaN. The cache ret5 channel (clipped at ±0.30)
         is NOT used.
  LIQ    log of 24h quote volume = log( Σ expm1(log_qv) · 288 / n ) over the 288 bars with close in (E−24h, E], log_qv = cache ch 3
         (= log1p(quote volume), wide_shadow bars_to_channels); n = bars with finite log_qv, NaN if n < 144.
  TBF    crowding proxy = simple mean of the taker-buy-fraction channel tbf = cache ch 6 (= taker-buy quote volume / quote volume per bar,
         NaN when quote volume is 0) over bars with close in (E−24h, E] that have log_cnt > 0 and finite tbf (frozen dead-contract rows have
         log_cnt == 0 and are therefore excluded; checked below that tbf is NaN on every log_cnt == 0 row); NaN if fewer than 48 such bars.
         Simple mean = the model features' definition (fea171 'tbf_mean_288').
  LIQ_EXCL / TBF_EXCL  sensitivity: the same with holefix-filled bars (holefix2_cells 6156f97a) removed (n scaled accordingly).
  FSIG   (added, not in the brief: it is the funding-momentum leg's own signal) = xz(f_fund_ema_v1[E, all 829]) — the rank position in
         [−0.5, 0.5] the fund leg uses (w10_health.py FZB, UMASK_SCOPE=m1).
Holefix policy: primary = INCL (filled bars used): the replay's P&L on those names over 2026-08-12..08-24 was itself computed from
filled-bar prices, so the characteristics use the same data; EXCL is reported as a sensitivity.
usage: python c0_chars.py <OUT_DIR>
"""
import json, os, sys, time, zipfile
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import c0_lib as L

T0 = time.time(); OUT = sys.argv[1]; os.makedirs(OUT, exist_ok=True)
chk = L.Checks(T0)
rec = {"device": "c0_chars.py", "self_sha256": L.sha(os.path.abspath(__file__)), "lib_sha256": L.sha(L.__file__), "numpy": np.__version__, "argv": sys.argv,
       "env": {k: os.environ[k] for k in sorted(os.environ)}, "utc_start": L.utc(time.time())}
rec["inputs"] = L.verify_inputs(chk, {**L.INPUTS, **L.CACHE_INPUTS})
if chk.fails:
    json.dump(rec | {"checks": chk.rows, "failed": chk.fails, "VERDICT": "REFUSED"}, open(f"{OUT}/RECEIPT_c0_chars.json", "w"), indent=1); sys.exit(3)
T_START = 1735689600       # 2025-01-01T00:00Z
C = L.load_common(chk)
A = L.load_arm("42", chk); A2 = L.load_arm("2027", chk)
ats = A["R"][:, 0].astype(np.int64)
chk("arms.same_anchor_axis", bool(np.array_equal(ats, A2["R"][:, 0].astype(np.int64))))
del A2
AX = ats[(ats >= T_START) & (ats <= L.UB)]; NA = len(AX)
chk("axis.anchors", NA > 3000, {"n": NA, "first": L.utc(AX[0]), "last": L.utc(AX[-1])})

# ---------------- cache: stream channels 3 (log_qv), 4 (log_cnt), 6 (tbf); first traded bar over the full history ----------------
CP = L.CACHE_INPUTS["CACHE_HOLEFIX2"][0]
ZC = np.load(CP); CTS = ZC["ts"].astype(np.int64); CH = [str(c) for c in ZC["ch"]]
chk("cache.channels", CH == ["ret5", "range", "cpos", "log_qv", "log_cnt", "log_avgsz", "tbf"] and [str(s) for s in ZC["symbols"]] == C["SYM"], CH)
chk("cache.grid", bool((np.diff(CTS) == 300).all()), {"first": L.utc(CTS[0]), "last": L.utc(CTS[-1]), "rows": len(CTS)})
crow = {int(t): r for r, t in enumerate(CTS)}
R0 = crow[int(AX[0])] - 287          # first cache row any 24h window needs
chk("cache.window_rows_available", R0 >= 1 and int(AX[-1]) in crow)
KEEP = np.empty((len(CTS) - R0, L.NW, 3), np.float16)
first_row = np.full(L.NW, -1, np.int64)
lc0_tbf_finite = 0; lc0_rows = 0
zf = zipfile.ZipFile(CP)
with zf.open("data.npy") as fh:
    ver = np.lib.format.read_magic(fh)
    shape, fort, dt = (np.lib.format.read_array_header_1_0(fh) if ver == (1, 0) else np.lib.format.read_array_header_2_0(fh))
    assert not fort and len(shape) == 3 and shape[0] == len(CTS) and shape[1] == L.NW and shape[2] == 7
    rowb = int(np.prod(shape[1:])) * dt.itemsize; r = 0; block = 8000
    while r < shape[0]:
        k = min(block, shape[0] - r); buf = fh.read(k * rowb); assert len(buf) == k * rowb
        X = np.frombuffer(buf, dtype=dt).reshape((k,) + tuple(shape[1:]))
        lc = X[:, :, 4].astype(np.float32); traded = np.isfinite(lc) & (lc > 0)
        has = traded.any(0); newf = has & (first_row < 0)
        if newf.any(): first_row[newf] = r + np.argmax(traded[:, newf], axis=0)
        z0 = np.isfinite(lc) & (lc == 0); lc0_rows += int(z0.sum()); lc0_tbf_finite += int((z0 & np.isfinite(X[:, :, 6])).sum())
        lo = max(r, R0); hi = r + k
        if hi > lo: KEEP[lo - R0:hi - R0] = X[lo - r:hi - r][:, :, [3, 4, 6]]
        r += k
del X, buf
chk("cache.tbf_nan_on_every_log_cnt_zero_row", lc0_tbf_finite == 0, {"log_cnt_zero_cells": lc0_rows, "of_which_tbf_finite": lc0_tbf_finite})
chk.log("cache streamed", KEEP.shape)
first_ts = np.where(first_row >= 0, CTS[np.maximum(first_row, 0)], -1)
censored = first_row == 0
rec["listing"] = {"names_with_trade": int((first_row >= 0).sum()), "left_censored_at_cache_start": int(censored.sum()),
                  "first_trade_in_holefix_cells": None}
HC = np.load(L.CACHE_INPUTS["HOLE_CELLS"][0]); hrow = HC["row"].astype(np.int64); hcol = HC["col"].astype(np.int64)
chk("holes.symbols_and_ts", [str(s) for s in HC["symbols"]] == C["SYM"] and bool(np.array_equal(HC["ts"].astype(np.int64), CTS[hrow])))
hset = set(zip(hrow.tolist(), hcol.tolist()))
rec["listing"]["first_trade_in_holefix_cells"] = [C["SYM"][c] for c in range(L.NW) if first_row[c] >= 0 and (int(first_row[c]), c) in hset]
FILL = np.zeros((len(CTS) - R0, L.NW), bool); sel_h = hrow >= R0; FILL[hrow[sel_h] - R0, hcol[sel_h]] = True
hf = FILL.any(0)
tbf_h = KEEP[:, :, 2][FILL]; lc_h = KEEP[:, :, 1][FILL]
rec["holefix_cells_in_window"] = {"cells": int(FILL.sum()), "names": int(hf.sum()), "tbf_finite_share": float(np.isfinite(tbf_h).mean()) if tbf_h.size else None,
                                  "traded_share": float((np.isfinite(lc_h) & (lc_h > 0)).mean()) if lc_h.size else None}
chk.log("holefix cells in window", rec["holefix_cells_in_window"])

# ---------------- per anchor ----------------
F32 = lambda: np.full((NA, L.NW), np.nan, np.float32)
AGE, RN8, MOM7, MOM30, LIQ, TBF, LIQX, TBFX, FSIG = (F32() for _ in range(9))
MEMB = np.zeros((NA, L.NW), bool)
Y4 = np.asarray(C["y4"], np.float64); LY = np.where(np.isfinite(Y4), np.log1p(np.where(np.isfinite(Y4), Y4, 0.0)), 0.0); BADY = ~np.isfinite(Y4)
cLY = np.vstack([np.zeros((1, L.NW)), np.cumsum(LY, 0)]); cBY = np.vstack([np.zeros((1, L.NW), np.int64), np.cumsum(BADY, 0)])
chk("meta.contiguous_4h", bool((np.diff(C["ME"]) == 14400).all()))
for a, E in enumerate(AX):
    i = C["mrow"][int(E)]; j = C["prow"][int(E)]
    m = L.members(C, i, j); MEMB[a, m] = True
    AGE[a] = np.where(first_ts >= 0, (E - first_ts) / 86400.0, np.nan)
    fn = np.asarray(C["FN"][j], np.float64); iv = np.asarray(C["IV"][j], np.float64)
    RN8[a] = fn * (8.0 / np.where(np.isfinite(iv) & (iv > 0), iv, 8.0))
    for n, OUTA in ((42, MOM7), (180, MOM30)):
        if i - n >= 0:
            s = cLY[i] - cLY[i - n]; b = cBY[i] - cBY[i - n]      # rows i-n .. i-1 = anchors E-n·4h .. E-4h
            OUTA[a] = np.where(b == 0, np.expm1(s), np.nan)
    rE = crow[int(E)] - R0; w = slice(rE - 287, rE + 1)
    qv = KEEP[w, :, 0].astype(np.float64); lc = KEEP[w, :, 1].astype(np.float64); tb = KEEP[w, :, 2].astype(np.float64); fl = FILL[w]
    for excl, OL, OT in ((False, LIQ, TBF), (True, LIQX, TBFX)):
        okq = np.isfinite(qv) & (~fl if excl else True); nq = okq.sum(0)
        vol = np.where(okq, np.expm1(np.where(okq, qv, 0.0)), 0.0).sum(0)
        with np.errstate(all="ignore"):
            OL[a] = np.where((nq >= 144) & (vol > 0), np.log(vol * 288.0 / np.maximum(nq, 1)), np.nan)
        okt = np.isfinite(tb) & np.isfinite(lc) & (lc > 0) & (~fl if excl else True); nt = okt.sum(0)
        with np.errstate(all="ignore"):
            OT[a] = np.where(nt >= 48, np.where(okt, tb, 0.0).sum(0) / np.maximum(nt, 1), np.nan)
    FSIG[a] = L.xz(np.asarray(C["FE"][j], np.float64))
    if a % 500 == 0: chk.log("anchor", a, "/", NA, L.utc(E))

# ---------------- cross-checks against the panel's own features (definitions differ; correlation only, not a gate) ----------------
PW = np.load(L.INPUTS["PANEL_ARM"][0], allow_pickle=True)
pj = np.array([C["prow"][int(E)] for E in AX])
def corr(x, y, msk):
    ok = msk & np.isfinite(x) & np.isfinite(y)
    return {"n": int(ok.sum()), "pearson": float(np.corrcoef(x[ok], y[ok])[0, 1]) if ok.sum() > 10 else None, "max_abs_diff": float(np.abs(x[ok] - y[ok]).max()) if ok.sum() else None}
rec["panel_crosscheck_members"] = {"TBF_vs_f_tbf_24h": corr(TBF, np.asarray(PW["f_tbf_24h"])[pj], MEMB), "MOM7_vs_f_mom_7d": corr(MOM7, np.asarray(PW["f_mom_7d"])[pj], MEMB),
                                   "MOM30_vs_f_mom_30d": corr(MOM30, np.asarray(PW["f_mom_30d"])[pj], MEMB)}
chk.log("panel crosscheck", rec["panel_crosscheck_members"])

# ---------------- member-count marginals (no weights, no P&L) ----------------
mon = np.array([time.strftime("%Y-%m", time.gmtime(int(t))) for t in AX]); months = sorted(set(mon.tolist()))
def q(x, msk): v = x[msk]; v = v[np.isfinite(v)]; return [float(t) for t in np.quantile(v, [0.01, 0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99])] if v.size else None
marg = {"quantiles_all_members": {}, "by_month": {}}
for nm, X in (("AGE", AGE), ("RN8_bp", RN8 * 1e4), ("MOM7", MOM7), ("MOM30", MOM30), ("LIQ", LIQ), ("TBF", TBF), ("FSIG", FSIG)):
    marg["quantiles_all_members"][nm] = q(X, MEMB)
rn = RN8 * 1e4
for mo in months:
    mk = MEMB & (mon == mo)[:, None]; n = int(mk.sum())
    d = {"member_cells": n}
    for nm, X in (("AGE", AGE), ("RN8", RN8), ("MOM7", MOM7), ("MOM30", MOM30), ("LIQ", LIQ), ("TBF", TBF), ("LIQ_EXCL", LIQX), ("TBF_EXCL", TBFX), ("FSIG", FSIG)):
        d[f"{nm}_nan_share"] = float((~np.isfinite(X[mk])).mean())
    ag = AGE[mk]
    d["AGE_share"] = {"lt30": float((ag < 30).mean()), "30_90": float(((ag >= 30) & (ag < 90)).mean()), "90_365": float(((ag >= 90) & (ag < 365)).mean()), "ge365": float((ag >= 365).mean())}
    r_ = rn[mk]
    d["RN8_share"] = {"le_-10bp": float((r_ <= -10).mean()), "-10_0": float(((r_ > -10) & (r_ < 0)).mean()), "0_to_base": float(((r_ >= 0) & (r_ < 1 - 1e-3)).mean()),
                      "base_1bp": float((np.abs(r_ - 1) <= 1e-3).mean()), "base_to_5bp": float(((r_ > 1 + 1e-3) & (r_ <= 5)).mean()), "gt_5bp": float((r_ > 5).mean()),
                      "nan": float((~np.isfinite(r_)).mean())}
    d["TBF_EXCL_label_differs_share_proxy"] = float((np.isfinite(TBF[mk]) != np.isfinite(TBFX[mk])).mean() + (np.isfinite(TBF[mk]) & np.isfinite(TBFX[mk]) & (TBF[mk] != TBFX[mk])).mean())
    marg["by_month"][mo] = d
rec["marginals"] = marg
out_npz = f"{OUT}/c0_chars.npz"
np.savez_compressed(out_npz, ts=AX, symbols=np.array(C["SYM"]), member=MEMB, AGE=AGE, RN8=RN8, MOM7=MOM7, MOM30=MOM30, LIQ=LIQ, TBF=TBF, LIQ_EXCL=LIQX, TBF_EXCL=TBFX,
                    FSIG=FSIG, first_trade_ts=first_ts, age_left_censored=censored, definitions=np.array(__doc__))
rec["outputs"] = {"chars": {"path": out_npz, "sha256": L.sha(out_npz)}}
rec.update({"checks": chk.rows, "n_checks": len(chk.rows), "failed": chk.fails, "VERDICT": "PASS" if not chk.fails else "FAIL", "runtime_s": round(time.time() - T0, 1),
            "utc_end": L.utc(time.time())})
json.dump(rec, open(f"{OUT}/RECEIPT_c0_chars.json", "w"), indent=1, default=str)
chk.log("VERDICT", rec["VERDICT"], "failed", chk.fails)
sys.exit(0 if not chk.fails else 3)
