"""NEWS P1: bitwise check column-restricted (pm ∪ BTC) vs full 829-column as-is producer mini; timing."""
import os, sys, json, time, calendar
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import news_hist_features as H
from t_one import load_common

def main():
    ts, syms, chn, D, holes, mk, cfg, crypto = load_common()
    anchors = [int(a) for a in sys.argv[1:]]
    mts = mk["ts"].astype(np.int64); out = []
    for A in anchors:
        cand = mk["mask"][int(np.searchsorted(mts, A))] & crypto
        t0 = time.time(); rf = H.replay_anchor(A, D, ts, syms, chn, cand, {}, {}, cfg["params"], cfg, f"{H.W}/work", holes=holes); tf = time.time() - t0
        t0 = time.time(); rm = H.replay_anchor(A, D, ts, syms, chn, cand, {}, {}, cfg["params"], cfg, f"{H.W}/work", holes=holes, cols="members"); tm = time.time() - t0
        eq82 = bool(np.array_equal(rf["X82"].view(np.uint16), rm["X82"].view(np.uint16)))
        eq89 = bool(np.array_equal(rf["X89"].view(np.uint32), rm["X89"].view(np.uint32)))
        r = {"utc": time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(A)), "n_members": int(len(rf["m"])), "full_s": round(tf, 1), "members_s": round(tm, 1),
             "X82_bitwise": eq82, "X89_bitwise": eq89, "X82_ndiff": int((rf["X82"].view(np.uint16) != rm["X82"].view(np.uint16)).sum()),
             "X89_ndiff": int((rf["X89"].view(np.uint32) != rm["X89"].view(np.uint32)).sum())}
        print(json.dumps(r), flush=True); out.append(r)
    json.dump(out, open(f"{H.W}/receipts/P1_COLRESTRICT_BITWISE.json", "w"), indent=1)

if __name__ == "__main__":
    main()
