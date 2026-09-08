"""GATE B1 — the rebuilt king side must reproduce the current book BITWISE on anchors <= 2026-08-10 20:00Z."""
import numpy as np, calendar, time, sys
HC = "/workspace/review_scratch/health_check"
COLS = ["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C = {c: i for i, c in enumerate(COLS)}
CUT = calendar.timegm((2026, 8, 10, 20, 0, 0))
fails = []
for s in ("42", "2027"):
    A = np.load("%s/dev_alt/probe_artifacts/w10_ablation_series_M1_UCRYPTO_prod_s%s_ccal.npz" % (HC, s), allow_pickle=True)
    B = np.load("%s/dev_hf/probe_artifacts/w10_ablation_series_HF_M1_UCRYPTO_s%s.npz" % (HC, s), allow_pickle=True)
    Ra, Rb = A["d30_n2_c42_rec"], B["d30_n2_c42_rec"]
    Wa, Wb = A["d30_n2_c42_W"], B["d30_n2_c42_W"]
    ta, tb = Ra[:, 0].astype(np.int64), Rb[:, 0].astype(np.int64)
    print("seed %s: anchors old %d new %d" % (s, len(ta), len(tb)), flush=True)
    ca = ta <= CUT; cb = tb <= CUT
    print("  anchors <= cut: old %d new %d  axis identical: %s" % (int(ca.sum()), int(cb.sum()), bool(ca.sum() == cb.sum() and (ta[ca] == tb[cb]).all())), flush=True)
    if ca.sum() != cb.sum() or not (ta[ca] == tb[cb]).all():
        fails.append((s, "axis")); continue
    for name, X, Y in (("rec", Ra[ca], Rb[cb]), ("W", Wa[ca], Wb[cb])):
        d = np.abs(np.nan_to_num(X.astype(np.float64)) - np.nan_to_num(Y.astype(np.float64)))
        nm = int((np.isfinite(X.astype(float)) ^ np.isfinite(Y.astype(float))).sum())
        print("  %-4s maxabs %.3e  nan_mismatch %d  cells %d -> %s" % (name, d.max(), nm, X.size, "OK" if (d.max() == 0.0 and nm == 0) else "FAIL"), flush=True)
        if d.max() != 0.0 or nm != 0: fails.append((s, name, float(d.max()), nm))
    # per-column detail on net_ex specifically
    a = Ra[ca, C["net_ex"]]; b = Rb[cb, C["net_ex"]]
    print("  net_ex   maxabs %.3e  mean old %+.6f new %+.6f" % (np.abs(a - b).max(), a.mean(), b.mean()), flush=True)
print("\nGATE_B1 %s" % ("FAIL %s" % fails if fails else "PASS — the rebuilt king side reproduces the current book bitwise on anchors <= 2026-08-10 20:00Z"), flush=True)
sys.exit(3 if fails else 0)
