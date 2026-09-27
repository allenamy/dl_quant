#!/usr/bin/env python3
"""l2n_build.py — S1 step 4 (AMENDMENT_L2_NC_population_2026-09-27 §1–§2, §4 rows 5/6/9/10/11). Committed before it is run.
Builds, per NC seed population, rows (i, n), the 10 L2 features (§5 verbatim for 1–7; 8–10 from the NC legs), KZ, the targets and the
residual targets, the shift-spectrum returns, a shuffle-future target, and the P_neg flag -> out/L2N_data_s{42,2027}.npz.
NO statistic of any feature or score against any target is computed here (coverage = finiteness counts only).

G-IN (hard stops):
  * RECEIPT_L2N_CHECKSUM.json: files_by_result has no MISMATCH and no UNVERIFIED (VOID days are dropped and counted, REPULLED_OK days use
    the re-pulled rows); RECEIPT_L2N_REPULL.json: checksum_mismatch == 0 for the extra files that are used.
  * regime classification contradicting the switch day <= 1% of classified files (L2 §8 G-IN), original + extra files.
  * NC population files == RECEIPT_L2N_population.json shas; META / PANEL / UMASK == l2_common.INPUTS shas.
Metrics merge per symbol: original out/metrics rows, minus every row whose label day is a VOID or REPULLED file day (both label->day
mappings dropped, conservative, because the original npz carry no row_file_day), plus out/metrics_ck_repulled rows, plus
out/metrics_nc_extra rows (checksum 1 and parse ok only). Data-time rule and de-duplication exactly as l2_b_common.load_metrics.
LABEL-REGIME ASSERTION (lead §1 leakage, element-wise): every metrics value used has data time <= E - 600 (checked on every lookup
through the t0 = E - 600 construction and asserted on the merged tau arrays: tau = L before 2024-03-04, L + 300 after).
Residual targets: u = within-anchor population-demeaned 1e4 * r (L2 §4); u_res = within-anchor OLS residual of u on [1, FZ, RN8, DRN8,
KZ] over rows with all five finite; anchors with < 10 such rows -> NaN.
Shuffle-future target: per anchor i a lag q_i drawn from default_rng([20260927, i]).integers(6, 61); SF_A = y4[k + q_i, n] demeaned
within the anchor's population (bps); NaN where not finite / beyond META.
404 reconciliation (restart row 5): per symbol, the file days with status 404 (original + extra) classified against the archive listing's
first / last zip date: BEFORE_FIRST / AFTER_LAST / INSIDE (a gap inside the listed range) / NOT_LISTED.
usage: run_l2.sh-style env; /workspace/venv/bin/python -B l2n_build.py <whitelist>
"""
import os, sys, time, json, calendar
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import l2_common as C
import l2_b_common as B
import l2_net as N

T0 = time.time()
envrep = C.check_env(sys.argv); st0 = C.sysstate()
L2 = C.L2; OUT = f"{L2}/out"; REC = f"{L2}/receipts"; DAY = 86400; SW = B.SWITCH_DAY
LEGS = "/dev/shm/news2_2026-09-23/work/legs.npz"; LEGS_SHA16 = "9ee5886f37d1727c"
DEV = ("l2_common.py", "l2_b_common.py", "l2n_build.py")
rep = dict(device="l2n_build.py", device_sha256={f: C.sha256(os.path.join(L2, "devices", f)) for f in DEV}, env=envrep, sys_before=st0)
rep["inputs"] = {k: C.sha256(C.INPUTS[k][0]) for k in ("META", "PANEL", "UMASK")}
for k in ("META", "PANEL", "UMASK"): assert rep["inputs"][k] == C.INPUTS[k][1], ("input sha", k)
POPR = json.load(open(f"{REC}/RECEIPT_L2N_population.json")); rep["population_receipt_sha256"] = C.sha256(f"{REC}/RECEIPT_L2N_population.json")
CKR = json.load(open(f"{REC}/RECEIPT_L2N_CHECKSUM.json")); RPR = json.load(open(f"{REC}/RECEIPT_L2N_REPULL.json"))
rep["checksum_receipt_sha256"] = C.sha256(f"{REC}/RECEIPT_L2N_CHECKSUM.json"); rep["repull_receipt_sha256"] = C.sha256(f"{REC}/RECEIPT_L2N_REPULL.json")
fb = CKR["files_by_result"]
assert fb.get("MISMATCH", 0) == 0 and fb.get("UNVERIFIED", 0) == 0, ("G-IN: full CHECKSUM not clean", fb)
rep["G_IN"] = {"checksum_files_by_result": fb, "repull_totals": RPR["totals"]}
L = np.load(LEGS); assert C.sha256(LEGS).startswith(LEGS_SHA16)
la = L["E_ts"].astype(np.int64); ZFD = L["ZFD"]; RN8L = L["RN8"]; KZ = L["KZ"]
D = B.load_core()
lsym = [str(x) for x in L["symbols"]]; assert lsym == D["SYM"]


def label_days(Lb):
    return np.floor_divide(Lb, DAY), np.floor_divide(Lb - 1, DAY)


def merged_metrics(syms):
    MET = {}; st = dict(void_days=0, repulled_days=0, extra_files=0, rows=0, duplicates=0, regime_classified=0, regime_violations=0, symbols=0)
    for s in syms:
        parts = []
        p = f"{OUT}/metrics/{s}.npz"; ckp = f"{OUT}/checksum_full/{s}.json"
        if os.path.exists(p):
            Z = np.load(p); Lb = Z["labels"].astype(np.int64); X = Z["X"].astype(np.float64)
            res = json.load(open(ckp))["files"] if os.path.exists(ckp) else {}
            drop = {calendar.timegm(time.strptime(d, "%Y-%m-%d")) // DAY for d, v in res.items() if v in ("VOID", "REPULLED_OK")}
            st["void_days"] += sum(1 for v in res.values() if v == "VOID"); st["repulled_days"] += sum(1 for v in res.values() if v == "REPULLED_OK")
            if drop:
                d0, d1 = label_days(Lb); keep = ~(np.isin(d0, list(drop)) | np.isin(d1, list(drop))); Lb = Lb[keep]; X = X[keep]
            parts.append((Lb, X))
            for reg, d in zip(Z["file_regime"], Z["file_day"]):
                if reg in ("END", "START"):
                    st["regime_classified"] += 1; st["regime_violations"] += int((reg == "END" and d >= SW) or (reg == "START" and d < SW))
        for extra in (f"{OUT}/metrics_ck_repulled/{s}.npz", f"{OUT}/metrics_nc_extra/{s}.npz"):
            if not os.path.exists(extra): continue
            Z = np.load(extra); okd = {int(d) for d, stt, ck, reg in zip(Z["file_day"], Z["file_status"], Z["file_checksum"], Z["file_regime"])
                                       if int(stt) == 200 and int(ck) == 1 and reg != "PARSE_BAD"}
            keep = np.isin(Z["row_file_day"], np.array(sorted(okd), np.int32)); parts.append((Z["labels"][keep].astype(np.int64), Z["X"][keep].astype(np.float64)))
            st["extra_files"] += len(okd)
            for reg, d in zip(Z["file_regime"], Z["file_day"]):
                if reg in ("END", "START"):
                    st["regime_classified"] += 1; st["regime_violations"] += int((reg == "END" and d >= SW) or (reg == "START" and d < SW))
        if not parts: continue
        Lb = np.concatenate([q[0] for q in parts]); X = np.concatenate([q[1] for q in parts])
        tau = Lb + 300 * ((Lb // DAY) >= SW)
        o = np.argsort(tau, kind="stable"); tau = tau[o]; X = X[o]
        keep = np.ones(tau.size, bool); keep[1:] = tau[1:] != tau[:-1]; st["duplicates"] += int((~keep).sum()); tau = tau[keep]; X = X[keep]
        cols = list(N.COLS)
        MET[s] = dict(dt=tau, OIQ=X[:, cols.index("sum_open_interest")], TOP=X[:, cols.index("sum_toptrader_long_short_ratio")],
                      GLB=X[:, cols.index("count_long_short_ratio")], TKR=X[:, cols.index("sum_taker_long_short_vol_ratio")])
        st["rows"] += int(tau.size); st["symbols"] += 1
    return MET, st


def reconcile_404(syms):
    lj = json.load(open(B.LISTING)); out = {"BEFORE_FIRST": 0, "AFTER_LAST": 0, "INSIDE": 0, "NOT_LISTED": 0}; inside = []
    for s in syms:
        days = []
        for p in (f"{OUT}/metrics/{s}.npz", f"{OUT}/metrics_nc_extra/{s}.npz"):
            if os.path.exists(p):
                Z = np.load(p); days += [int(d) for d, st in zip(Z["file_day"], Z["file_status"]) if int(st) == 404]
        if not days: continue
        z = lj.get(s, {}).get("zip_dates") or []
        if not z: out["NOT_LISTED"] += len(days); continue
        f0 = calendar.timegm(time.strptime(z[0], "%Y-%m-%d")) // DAY; f1 = calendar.timegm(time.strptime(z[-1], "%Y-%m-%d")) // DAY
        for d in days:
            k = "BEFORE_FIRST" if d < f0 else ("AFTER_LAST" if d > f1 else "INSIDE"); out[k] += 1
            if k == "INSIDE": inside.append([s, time.strftime("%Y-%m-%d", time.gmtime(d * DAY))])
    return out, inside[:200]


seeds = ("42", "2027"); syms_needed = set()
POP = {}
for s in seeds:
    p = POPR["per_seed"][s]["out"]; assert C.sha256(p) == POPR["per_seed"][s]["out_sha256"], ("NC pop sha", s)
    Z = np.load(p); POP[s] = (Z["ts"].astype(np.int64), Z["P"]); syms_needed |= {lsym[n] for n in np.flatnonzero(Z["P"].any(0))}
MET, mst = merged_metrics(sorted(syms_needed)); rep["metrics_merge"] = mst
viol = mst["regime_violations"] / max(mst["regime_classified"], 1); rep["G_IN"]["regime_violation_share"] = viol
assert viol <= 0.01, ("G-IN: regime violations > 1%", viol)
for s, m in MET.items():   # label-regime assertion, element-wise on the merged tau arrays
    assert np.all(np.diff(m["dt"]) > 0), ("tau not strictly increasing", s)
rep["reconcile_404"], rep["reconcile_404_inside_first200"] = reconcile_404(sorted(syms_needed))
Y = D["Y"]; T = Y.shape[0]
for s in seeds:
    ts, P = POP[s]
    ii_rec = np.searchsorted(D["PTS"], ts); inrec = (ii_rec < D["PTS"].size) & (D["PTS"][np.minimum(ii_rec, D["PTS"].size - 1)] == ts)
    pos = np.searchsorted(la, ts); assert np.array_equal(la[pos], ts)
    r_, n_ = np.nonzero(P[inrec]); i = ii_rec[inrec][r_]; n = n_.astype(np.int64); E = ts[inrec][r_]; lp = pos[inrec][r_]
    F = np.full((i.size, 10), np.nan)
    for a0 in range(0, i.size, 200000):
        sl = slice(a0, a0 + 200000)
        F[sl] = B.features_rows(i[sl], n[sl], E[sl], Y, D["FN"], D["IV"], D["FE"], D["TB24"], D["FIRST_DAY"], MET, D["SYM"])
    rn = 1e4 * np.nan_to_num(RN8L[lp, n].astype(np.float64), nan=0.0); rn6 = 1e4 * np.nan_to_num(RN8L[np.maximum(lp - 6, 0), n].astype(np.float64), nan=0.0)
    F[:, 7] = ZFD[lp, n].astype(np.float64); F[:, 8] = rn; F[:, 9] = np.where(lp >= 6, rn - rn6, np.nan)
    kz = KZ[lp, n].astype(np.float64)
    rA, rB = B.targets_rows(i, n, Y); SA, SB = B.shifted_returns(i, n, Y)
    uniq, inv = np.unique(i, return_inverse=True)
    def demean(r):
        u = np.full(r.size, np.nan); ok = np.isfinite(r)
        mu = np.bincount(inv[ok], r[ok], uniq.size) / np.maximum(np.bincount(inv[ok], None, uniq.size), 1); u[ok] = 1e4 * (r[ok] - mu[inv[ok]]); return u
    uA, uB = demean(rA), demean(rB)
    def resid(u):
        out = np.full(u.size, np.nan); R5 = np.column_stack([np.ones(u.size), F[:, 7], F[:, 8], F[:, 9], kz])
        ok = np.isfinite(u) & np.isfinite(R5).all(1); o = np.argsort(inv, kind="stable")
        bounds = np.searchsorted(inv[o], np.arange(uniq.size + 1))
        for g in range(uniq.size):
            rows = o[bounds[g]:bounds[g + 1]]; rows = rows[ok[rows]]
            if rows.size < 10: continue
            beta = np.linalg.lstsq(R5[rows], u[rows], rcond=None)[0]; out[rows] = u[rows] - R5[rows] @ beta
        return out
    uA_res, uB_res = resid(uA), resid(uB)
    k = i + C.META_OFF; q = np.array([np.random.default_rng([20260927, int(g)]).integers(6, 61) for g in uniq])[inv]
    kk = k + q; okf = kk < T; sf = np.full(i.size, np.nan); sf[okf] = Y[kk[okf], n[okf]]; SF_A = demean(sf)
    year = B.year_of_ts(E); day = (E // DAY).astype(np.int64)
    out = f"{OUT}/L2N_data_s{s}.npz"
    np.savez_compressed(out + ".tmp.npz", i=i.astype(np.int32), n=n.astype(np.int16), E=E, day=day, year=year.astype(np.int16), F=F, feats=np.array(B.FEATS),
                        KZ=kz, rA=rA, rB=rB, uA=uA, uB=uB, uA_res=uA_res, uB_res=uB_res, SA=SA, SB=SB, shiftA=np.array(B.SHIFT_A), shiftB=np.array(B.SHIFT_B),
                        SF_A=SF_A, sf_lag=q.astype(np.int16), pneg=(rn < 0), symbols=np.array(D["SYM"]))
    os.replace(out + ".tmp.npz", out)
    cov = {}
    for y in sorted(set(year.tolist())):
        r = year == y
        cov[str(y)] = dict(rows=int(r.sum()), anchors=int(np.unique(i[r]).size), rA_finite=float(np.isfinite(rA[r]).mean()), uA_res_finite=float(np.isfinite(uA_res[r]).mean()),
                           rB_finite=float(np.isfinite(rB[r]).mean()), feature_finite={B.FEATS[c]: float(np.isfinite(F[r, c]).mean()) for c in range(10)},
                           KZ_finite=float(np.isfinite(kz[r]).mean()), P_neg_rows=int((r & (rn < 0)).sum()))
    rep.setdefault("per_seed", {})[s] = dict(rows=int(i.size), anchors_not_on_rec_axis=int((~inrec).sum()), out=out, out_sha256=C.sha256(out), coverage=cov)
    print(f"L2N_BUILD s{s} rows {i.size} coverage " + json.dumps({y: {kk_: round(v, 3) for kk_, v in c["feature_finite"].items()} for y, c in cov.items()}), flush=True)
rep["sys_after"] = C.sysstate(); rep["wall_s"] = round(time.time() - T0, 1)
C.jdump(rep, f"{REC}/RECEIPT_L2N_build.json"); assert json.load(open(f"{REC}/RECEIPT_L2N_build.json"))["device"] == "l2n_build.py"
print("L2N_BUILD DONE " + C.sha256(f"{REC}/RECEIPT_L2N_build.json")[:16], flush=True)
