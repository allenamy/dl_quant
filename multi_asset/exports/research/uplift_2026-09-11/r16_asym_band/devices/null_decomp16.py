"""r16 receipt: treatment vs matched-null decomposition on W_ALPHA, incl. step-level exempt |dw| and book-level
marginal turnover (the nulls are matched at the exemption step; realized book turnover is NOT constrained)."""
import numpy as np, calendar, hashlib
R = "/workspace/uplift_2026-09-11/r16_asym_band/arms/"
assert hashlib.sha256(open("/workspace/uplift_2026-09-11/r16_asym_band/PREREG_r16_asym_band_2026-09-12.md", "rb").read()).hexdigest() == "68bc4fdb7f619dbb9ca10fc868f86b1f31f227029f7b58aead309f4620ab2b0c"
def ld(t):
    Z = np.load(R + t + ".npz", allow_pickle=True); return Z["rec"], Z["R16A"], {str(c): i for i, c in enumerate(Z["R16A_cols"])}
TS = calendar.timegm((2026, 8, 30, 20, 0, 0))
for sd in (42, 2027):
    r0, a0, ac = ld("GP_s%d_aux1" % sd); ts = r0[:, 0].astype(np.int64); m = ts <= TS; m[:900] = False
    base = lambda rec, c: (rec[m, c] / rec[m, 5]).mean()
    print("== seed", sd, "W_ALPHA n", int(m.sum()))
    for x in ("X0", "X1", "X2", "X3", "X4", "X5"):
        rt, at, _ = ld("A_%s_s%d" % (x, sd))
        ex = lambda A: (A[m, ac["k_exempt_abs_dw"]] + A[m, ac["f_exempt_abs_dw"]]).mean()
        nx = lambda A: (A[m, ac["k_n_exempt"]] + A[m, ac["f_n_exempt"]]).mean()
        print("%s treat: dg %+.4f dpnl %+.4f dcarry %+.4f dcost %+.4f dturn_file %+.5f step_exempt_|dw|/anchor %.5f n_exempt/anchor %.1f" %
              (x, base(rt, 18) - base(r0, 18), base(rt, 19) - base(r0, 19), base(rt, 20) - base(r0, 20), base(rt, 21) - base(r0, 21), base(rt, 17) - base(r0, 17), ex(at), nx(at)))
        for d in (1, 2, 3):
            rn, an, _ = ld("N_%s_d%d_s%d" % (x, d, sd))
            print("  null d%d: dg %+.4f dpnl %+.4f dcarry %+.4f dcost %+.4f dturn_file %+.5f step_exempt_|dw| %.5f n_exempt %.1f | gross-of-cost (dpnl-dcarry) treat-null %+.4f | net treat-null %+.4f" %
                  (d, base(rn, 18) - base(r0, 18), base(rn, 19) - base(r0, 19), base(rn, 20) - base(r0, 20), base(rn, 21) - base(r0, 21), base(rn, 17) - base(r0, 17), ex(an), nx(an),
                   (base(rt, 19) - base(rt, 20)) - (base(rn, 19) - base(rn, 20)), base(rt, 18) - base(rn, 18)))
