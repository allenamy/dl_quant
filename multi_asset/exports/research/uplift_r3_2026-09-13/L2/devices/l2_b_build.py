"""l2_b_build.py — PREREG_L2 §3–§5: population rows, targets, features, shift-return arrays → out/L2_B_data_s{42,2027}.npz.
G-IN: all input shas; POP masks recomputed from the arms bitwise; METRICS manifest sha == RECEIPT_L2_B_pull.json; pull totals
(unresolved checksum mismatches 0, failed files reported, regime-classification violations <= 1% of classified files).
Writes RECEIPT_L2_B_build.json (feature coverage by year, target counts, metrics duplicate stats). No statistic of features vs targets."""
import os, sys, time, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import l2_common as C
import l2_b_common as B

T_START = time.time()
envrep = C.check_env(sys.argv); pre = B.check_prereg()
st0 = C.sysstate(); assert st0["gpu"].replace(" ", "") == "0%,2MiB", st0["gpu"]
DEV = ("l2_common.py", "l2_b_common.py", "l2_b_build.py", "run_l2.sh")
rep = dict(device="l2_b_build.py", device_sha256={f: C.sha256(os.path.join(C.L2, "devices", f)) for f in DEV}, prereg=pre, env=envrep, sys_before=st0)
rep["inputs"] = C.input_shas(check=True)
for s, (p, sh) in B.POP_FILES.items():
    assert C.sha256(p) == sh, ("POP sha", s)
pull = json.load(open(B.PULL_RECEIPT)); tot = pull["totals"]
man_sha = C.sha256(os.path.join(B.METDIR, "MANIFEST.json"))
assert man_sha == pull["manifest"]["sha256"], "METRICS manifest changed since the pull receipt"
man = json.load(open(os.path.join(B.METDIR, "MANIFEST.json")))
unresolved = sum(int(e.get("checksum_mismatch", 0)) for e in man.values())
classified = tot["regime_counts"]["END"] + tot["regime_counts"]["START"]
viol_share = tot["regime_violations"] / max(classified, 1)
rep["G_IN"] = dict(pull_receipt_sha256=C.sha256(B.PULL_RECEIPT), manifest_sha256=man_sha, checksum_mismatch=unresolved, files_failed=tot.get("files_failed"),
                   files_200=tot["files_200"], regime_counts=tot["regime_counts"], regime_violations=tot["regime_violations"], regime_violation_share=viol_share)
assert unresolved == 0, ("G-IN: unresolved CHECKSUM mismatches", unresolved)
assert viol_share <= 0.01, ("G-IN: regime classification contradicts the switch day for > 1% of classified files", viol_share)
D = B.load_core()
rep["listing_sha256"] = C.sha256(B.LISTING)
Dm, readers = C.load_axis_and_masks()   # for POP recompute (T1MEM, qvk); arrays read are non-return
for s in C.SEEDS:
    A = C.load_arm(s, Dm)
    Zp = np.load(B.POP_FILES[s][0]); Pf = Zp["P"]
    mism = 0
    for i in range(C.N_FULL):
        P, _, _ = C.population_row(A["SMRC"][i], A["MEM"][i])
        mism += int((P != Pf[i]).sum())
    assert mism == 0, ("G-IN: POP mask differs from the arm recomputation", s, mism)
    rep.setdefault("G_IN_pop_recompute_mismatch", {})[s] = mism
    del A
C.assert_no_returns_read(readers)
syms_needed = sorted({D["SYM"][n] for s in C.SEEDS for n in np.nonzero(np.load(B.POP_FILES[s][0])["P"].any(axis=0))[0]})
MET, mrep = B.load_metrics(syms_needed)
rep["metrics_load"] = mrep; rep["metrics_symbols_missing"] = sorted(set(syms_needed) - set(MET))
for s in C.SEEDS:
    Zp = np.load(B.POP_FILES[s][0]); Pf = Zp["P"]; smr = Zp["smr"].astype(np.float64); rn8 = Zp["rn8_device"].astype(np.float64)
    ii, nn = np.nonzero(Pf)                  # row-major: sorted by i then n
    E = D["PTS"][ii]
    F = np.full((ii.size, 10), np.nan)
    CH = 200000
    for a0 in range(0, ii.size, CH):
        sl = slice(a0, a0 + CH)
        F[sl] = B.features_rows(ii[sl], nn[sl], E[sl], D["Y"], D["FN"], D["IV"], D["FE"], D["TB24"], D["FIRST_DAY"], MET, D["SYM"])
    rA, rB = B.targets_rows(ii, nn, D["Y"])
    assert np.isfinite(rA).all(), ("N2 fact violated: non-finite r_A in the population", s, int((~np.isfinite(rA)).sum()))
    SA, SB = B.shifted_returns(ii, nn, D["Y"])
    assert np.array_equal(SA[:, B.SHIFT_A.index(0)], rA, equal_nan=True) and np.array_equal(SB[:, B.SHIFT_B.index(0)], rB, equal_nan=True)
    # within-anchor population demeaning (bps)
    uA = np.full(ii.size, np.nan); uB = np.full(ii.size, np.nan)
    uniq, inv = np.unique(ii, return_inverse=True)
    for r, u in ((rA, uA), (rB, uB)):
        ok = np.isfinite(r)
        mu = np.bincount(inv[ok], r[ok], uniq.size) / np.maximum(np.bincount(inv[ok], None, uniq.size), 1)
        u[ok] = 1e4 * (r[ok] - mu[inv[ok]])
    year = B.year_of_ts(E); day = (E // B.DAY).astype(np.int64)
    out = os.path.join(C.L2, "out", "L2_B_data_s%s.npz" % s)
    np.savez_compressed(out + ".tmp.npz", i=ii.astype(np.int32), n=nn.astype(np.int16), E=E, day=day, year=year.astype(np.int16), F=F, feats=np.array(B.FEATS),
                        rA=rA, rB=rB, uA=uA, uB=uB, SA=SA, SB=SB, shiftA=np.array(B.SHIFT_A), shiftB=np.array(B.SHIFT_B), absmr=np.abs(smr[ii, nn]),
                        rn8=rn8[ii, nn], symbols=np.array(D["SYM"]))
    os.replace(out + ".tmp.npz", out)
    cov = {}
    for y in (2022,) + B.TEST_YEARS:
        r = year == y
        cov[str(y)] = dict(rows=int(r.sum()), anchors=int(np.unique(ii[r]).size), rB_finite=float(np.isfinite(rB[r]).mean()) if r.any() else None,
                           feature_finite={B.FEATS[c]: float(np.isfinite(F[r, c]).mean()) if r.any() else None for c in range(10)},
                           P_neg_rows=int((r & (rn8[ii, nn] < 0)).sum()))
    rep.setdefault("per_seed", {})[s] = dict(rows=int(ii.size), out=out, out_sha256=C.sha256(out), out_size=os.path.getsize(out), coverage=cov)
    print("seed %s rows %d coverage %s" % (s, ii.size, json.dumps({y: {k: (round(v, 3) if isinstance(v, float) else v) for k, v in c["feature_finite"].items()} for y, c in cov.items()})), flush=True)
st1 = C.sysstate(); rep["sys_after"] = st1; rep["wall_s"] = round(time.time() - T_START, 1)
assert st1["gpu"].replace(" ", "") == "0%,2MiB", st1["gpu"]
C.jdump(rep, os.path.join(C.L2, "receipts", "RECEIPT_L2_B_build.json"))
print("SUMMARY l2_b_build OK rows s42=%d s2027=%d metrics_symbols=%d missing=%d wall=%.0fs" % (
    rep["per_seed"]["42"]["rows"], rep["per_seed"]["2027"]["rows"], mrep["symbols"], len(rep["metrics_symbols_missing"]), rep["wall_s"]), flush=True)
