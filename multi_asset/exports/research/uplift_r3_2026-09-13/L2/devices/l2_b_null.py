"""l2_b_null.py — PREREG_L2 §8 G-NULL: day-block circular-permutation family-min null for the 4 gate cells {R, L} × {A, B} (FULL, P_all), per seed.
Replicate ρ uses a whole-day shift L_ρ (500 shifts drawn without replacement from [30, span_days − 30] with default_rng([20260913, 8]));
the target time axis is cyclically shifted by 6·L_ρ anchors within the test window for ALL names at once (row (i, n) receives the target of
(i + 6·L_ρ wrapped, n)); scores and top-decile flags stay fixed; rows whose shifted target is non-finite are dropped and anchors keep >= 10 rows.
This preserves each name's return distribution, the 24h target overlap and the cross-section, and breaks only score–target alignment
(pre-freeze synthetic calibration: the within-anchor key permutation gave null SD 1.87 vs true 3.73 bps for target B; the circular shift 4.12).
Per cell z = G / sd_null; family statistic = min over cells; threshold q05. Writes out/L2_B_null_s{seed}.npz and RECEIPT_L2_B_null.json."""
import os, sys, time, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import l2_common as C
import l2_b_common as B

T_START = time.time()
envrep = C.check_env(sys.argv); pre = B.check_prereg()
st0 = C.sysstate(); assert st0["gpu"].replace(" ", "") == "0%,2MiB", st0["gpu"]
DEV = ("l2_common.py", "l2_b_common.py", "l2_b_null.py", "run_l2.sh")
rep = dict(device="l2_b_null.py", device_sha256={f: C.sha256(os.path.join(C.L2, "devices", f)) for f in DEV}, prereg=pre, env=envrep, sys_before=st0, per_seed={})
brc_p = os.path.join(C.L2, "receipts", "RECEIPT_L2_B_build.json"); brc = json.load(open(brc_p))
frc_p = os.path.join(C.L2, "receipts", "RECEIPT_L2_B_fit.json"); frc = json.load(open(frc_p))
rep["build_receipt_sha256"] = C.sha256(brc_p); rep["fit_receipt_sha256"] = C.sha256(frc_p)
D = B.load_core(); Y = D["Y"]
for s in C.SEEDS:
    Z = np.load(brc["per_seed"][s]["out"]); assert C.sha256(brc["per_seed"][s]["out"]) == brc["per_seed"][s]["out_sha256"]
    O = np.load(frc["out"][s]["path"]); assert C.sha256(frc["out"][s]["path"]) == frc["out"][s]["sha256"]
    I = Z["i"].astype(np.int64); Nn = Z["n"].astype(np.int64); YR = Z["year"].astype(np.int64)
    # the test window in rec rows (common to both targets): first..last test-year rec row, whole days
    trows = I[YR >= 2023]; lo_i = int(trows.min()); hi_i = int(trows.max()); span = hi_i - lo_i + 1
    assert span % 6 == 0 and lo_i % 6 == 0, (lo_i, span)
    span_days = span // 6
    shifts = np.random.default_rng([20260913, 8]).choice(np.arange(30, span_days - 30), size=B.NNULL, replace=False)
    prep = {}
    for T in B.TARGETS:
        r = Z["r" + T]; ok = (YR >= 2023) & np.isfinite(r)
        idx, a, sizes, _ = B.anchor_index(I, ok)
        big = sizes[a] >= B.MIN_ANCHOR
        idx, a, sizes, _ = B.anchor_index(I, np.isin(np.arange(I.size), idx[big]))
        sv = -1e4 * r[idx]; col = Nn[idx]
        cells = {}
        for m in B.MODELS:
            p = O["p_%s_%s_FULL" % (m, T)][idx]; assert np.isfinite(p).all()
            top, bot, mm = B.decile_sets(p, a, sizes, col)
            Dv, _ = B.anchor_stats(sv, a, sizes, top, bot)
            cells[m] = dict(top=top, G=float(Dv.mean()))
        prep[T] = dict(idx=idx, a=a, sizes=sizes, cells=cells, rows_i=I[idx], nn=Nn[idx])
    names = ["%s_%s" % (m, T) for m in B.MODELS for T in B.TARGETS]
    NUL = np.full((B.NNULL, len(names)), np.nan); kept = np.zeros((B.NNULL, 2))
    for rho, sh in enumerate(shifts):
        for tq, T in enumerate(B.TARGETS):
            q = prep[T]; i2 = lo_i + ((q["rows_i"] - lo_i + 6 * int(sh)) % span)
            rA2, rB2 = B.targets_rows(i2, q["nn"], Y)
            s2 = -1e4 * (rA2 if T == "A" else rB2); okr = np.isfinite(s2)
            aa = q["a"][okr]; ss = s2[okr]; na = q["sizes"].size
            cnt = np.bincount(aa, None, na); pop = np.bincount(aa, ss, na)
            kept[rho, tq] = okr.mean()
            for m in B.MODELS:
                tt = q["cells"][m]["top"][okr].astype(np.float64)
                ct = np.bincount(aa, tt, na); good = (cnt >= B.MIN_ANCHOR) & (ct > 0)
                Dn = np.bincount(aa, ss * tt, na)[good] / ct[good] - pop[good] / cnt[good]
                NUL[rho, names.index("%s_%s" % (m, T))] = Dn.mean()
        if rho % 100 == 0:
            print("seed %s null %d/%d %.0fs" % (s, rho, B.NNULL, time.time() - T_START), flush=True)
    assert np.isfinite(NUL).all()
    sd = NUL.std(axis=0, ddof=1)
    zN = NUL / sd[None, :]; fam = zN.min(axis=1); q05 = float(np.quantile(fam, 0.05))
    obs = {nm: prep[nm.split("_")[1]]["cells"][nm.split("_")[0]]["G"] for nm in names}
    zobs = {nm: obs[nm] / sd[names.index(nm)] for nm in names}
    op = os.path.join(C.L2, "out", "L2_B_null_s%s.npz" % s)
    np.savez_compressed(op + ".tmp.npz", null_G=NUL, names=np.array(names), shifts_days=shifts, kept_share=kept); os.replace(op + ".tmp.npz", op)
    rep["per_seed"][s] = dict(names=names, test_window_rec_rows=[lo_i, hi_i], span_days=span_days, sd_null={nm: float(sd[names.index(nm)]) for nm in names},
                              mean_null={nm: float(NUL[:, names.index(nm)].mean()) for nm in names}, family_min_q05=q05,
                              family_min_quantiles={str(qq): float(np.quantile(fam, qq)) for qq in (0.01, 0.05, 0.10, 0.50)},
                              kept_share_mean={"A": float(kept[:, 0].mean()), "B": float(kept[:, 1].mean())},
                              z_obs=zobs, out=op, out_sha256=C.sha256(op), anchors={T: int(prep[T]["sizes"].size) for T in B.TARGETS})
    print("seed %s q05 %.3f z_obs %s" % (s, q05, json.dumps({k: round(v, 3) for k, v in zobs.items()})), flush=True)
st1 = C.sysstate(); assert st1["gpu"].replace(" ", "") == "0%,2MiB", st1["gpu"]
rep.update(sys_after=st1, wall_s=round(time.time() - T_START, 1))
C.jdump(rep, os.path.join(C.L2, "receipts", "RECEIPT_L2_B_null.json"))
print("SUMMARY l2_b_null OK replicates=%d wall=%.0fs" % (B.NNULL, rep["wall_s"]), flush=True)
