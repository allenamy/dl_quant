"""l2_b_fit.py — PREREG_L2 §6: the 96 fits {R, L} × {A, B} × {FULL, BASE, DESC} × {2023..2026} × {s42, s2027} → out-of-sample scores.
Training for test year Y: population rows with E < Y-01-01 00:00Z − 24h and finite target; evaluation: rows of year Y with finite target.
Label = within-anchor population-demeaned return u (bps), clipped at training [0.5%, 99.5%]. Scores saved per cell in out/L2_B_oos_s{seed}.npz.
No statistic of scores against targets is computed here."""
import os, sys, time, json, calendar
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import l2_common as C
import l2_b_common as B

T_START = time.time()
envrep = C.check_env(sys.argv); pre = B.check_prereg()
st0 = C.sysstate(); assert st0["gpu"].replace(" ", "") == "0%,2MiB", st0["gpu"]
DEV = ("l2_common.py", "l2_b_common.py", "l2_b_fit.py", "run_l2.sh")
rep = dict(device="l2_b_fit.py", device_sha256={f: C.sha256(os.path.join(C.L2, "devices", f)) for f in DEV}, prereg=pre, env=envrep, sys_before=st0, fits={})
import lightgbm as lgb
rep["lightgbm"] = lgb.__version__; assert lgb.__version__ == "4.7.0", lgb.__version__
brc_p = os.path.join(C.L2, "receipts", "RECEIPT_L2_B_build.json"); brc = json.load(open(brc_p)); rep["build_receipt_sha256"] = C.sha256(brc_p)
str_ = os.path.join(C.L2, "receipts", "RECEIPT_L2_B_selftest.json"); stc = json.load(open(str_)); rep["selftest_receipt_sha256"] = C.sha256(str_)
assert all(stc["gates"].values()), ("selftest gates not all passed", stc["gates"])
n_fits = 0
for s in C.SEEDS:
    DATA = brc["per_seed"][s]["out"]; assert C.sha256(DATA) == brc["per_seed"][s]["out_sha256"]
    Z = np.load(DATA); E = Z["E"]; YR = Z["year"].astype(np.int64); F = Z["F"]
    out = {}
    for T in B.TARGETS:
        u = Z["u" + T]
        for fs, cols in B.FSETS.items():
            X = F[:, cols]
            for m in B.MODELS:
                p = np.full(E.size, np.nan)
                for Y in B.TEST_YEARS:
                    y0 = calendar.timegm((Y, 1, 1, 0, 0, 0))
                    tr = (E < y0 - 86400) & np.isfinite(u)
                    te = (YR == Y) & np.isfinite(u)
                    t1 = time.time()
                    pred, info = B.fit_predict(m, X[tr], u[tr], X[te])
                    assert np.isfinite(pred).all(), ("non-finite predictions", s, T, fs, m, Y)
                    p[te] = pred; n_fits += 1
                    info.update(train_last=C.utc(E[tr].max()), test_first=C.utc(E[te].min()), test_last=C.utc(E[te].max()), fit_s=round(time.time() - t1, 1))
                    rep["fits"]["%s|%s|%s|%s|%d" % (s, T, fs, m, Y)] = info
                    print("fit s%s %s %s %s %d n_train %d n_test %d %.1fs" % (s, T, fs, m, Y, info["n_train"], info["n_test"], info["fit_s"]), flush=True)
                out["p_%s_%s_%s" % (m, T, fs)] = p
    op = os.path.join(C.L2, "out", "L2_B_oos_s%s.npz" % s)
    np.savez_compressed(op + ".tmp.npz", **out); os.replace(op + ".tmp.npz", op)
    rep.setdefault("out", {})[s] = dict(path=op, sha256=C.sha256(op), size=os.path.getsize(op), keys=sorted(out))
assert n_fits == 96, n_fits
st1 = C.sysstate(); assert st1["gpu"].replace(" ", "") == "0%,2MiB", st1["gpu"]
rep.update(n_fits=n_fits, sys_after=st1, wall_s=round(time.time() - T_START, 1))
C.jdump(rep, os.path.join(C.L2, "receipts", "RECEIPT_L2_B_fit.json"))
print("SUMMARY l2_b_fit OK fits=%d wall=%.0fs" % (n_fits, rep["wall_s"]), flush=True)
