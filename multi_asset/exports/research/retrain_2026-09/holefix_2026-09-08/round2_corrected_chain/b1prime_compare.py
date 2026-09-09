"""B1': two replay artifacts must be BITWISE identical (rec 23 cols + weight matrix W) on anchors <= CUT. usage: b1prime_compare.py <old.npz> <new.npz> [cut_iso]"""
import numpy as np, sys, calendar, time
A = np.load(sys.argv[1], allow_pickle=True); B = np.load(sys.argv[2], allow_pickle=True)
CUT = calendar.timegm(tuple(int(x) for x in sys.argv[3].replace("T", "-").replace(":", "-").split("-")[:5]) + (0,)) if len(sys.argv) > 3 else calendar.timegm((2026, 8, 10, 20, 0, 0))
Ra, Rb = A["d30_n2_c42_rec"], B["d30_n2_c42_rec"]; Wa, Wb = A["d30_n2_c42_W"], B["d30_n2_c42_W"]
ta, tb = Ra[:, 0].astype(np.int64), Rb[:, 0].astype(np.int64); ca, cb = ta <= CUT, tb <= CUT
print("anchors old %d new %d | <=cut old %d new %d | axis identical <=cut: %s" % (len(ta), len(tb), ca.sum(), cb.sum(), bool(ca.sum() == cb.sum() and (ta[ca] == tb[cb]).all())))
ok = ca.sum() == cb.sum() and (ta[ca] == tb[cb]).all()
if ok:
    for nm, X, Y in (("rec", Ra[ca], Rb[cb]), ("W", Wa[ca], Wb[cb])):
        X = X.astype(np.float64); Y = Y.astype(np.float64); d = np.abs(np.nan_to_num(X) - np.nan_to_num(Y)); nm_ = int((np.isfinite(X) ^ np.isfinite(Y)).sum())
        print("  %-4s maxabs %.3e nan_mismatch %d cells %d -> %s" % (nm, d.max(), nm_, X.size, "OK" if (d.max() == 0 and nm_ == 0) else "FAIL")); ok &= (d.max() == 0 and nm_ == 0)
    print("  net_ex mean <=cut: old %+.6f new %+.6f" % (Ra[ca, 18].mean(), Rb[cb, 18].mean()))
    extra = tb[~cb]; print("  new anchors beyond cut: %d (%s .. %s)" % (len(extra), time.strftime("%F %H:%MZ", time.gmtime(extra[0])) if len(extra) else "-", time.strftime("%F %H:%MZ", time.gmtime(extra[-1])) if len(extra) else "-"))
print("B1PRIME %s" % ("PASS" if ok else "FAIL")); sys.exit(0 if ok else 3)
