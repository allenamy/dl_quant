import os
from multi_asset.train.train_dual_lob import _build_folds
days = sorted(f[:-4] for f in os.listdir("data/npz_v2arch") if f.endswith(".npz") and f[0].isdigit())
print("cache days:", len(days), "span", days[0], "->", days[-1])
for m, ts in [("01","2025-01-10"),("02","2025-02-10"),("03","2025-03-10"),("04","2025-04-10"),("05","2025-05-10"),("06","2025-06-10"),("07","2025-07-10")]:
    tcfg = dict(train_days=450, val_days=45, test_days=28, fold_test_starts=[ts])
    try:
        f = _build_folds(days, tcfg, embargo_days=1)[0]
        tr = f["train"]; ok = len(tr) == 450
        status = "FULL-450 OK" if ok else "*** TRUNCATED (%d) ***" % len(tr)
        print("wf_2025_%s ts=%s: train=%dd [%s..%s] %s | val[%s..%s] test[%s..%s]" % (
            m, ts, len(tr), tr[0], tr[-1], status, f["val"][0], f["val"][-1], f["test"][0], f["test"][-1]))
    except Exception as e:
        print("wf_2025_%s: ERROR %s" % (m, e))
